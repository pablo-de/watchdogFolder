import os
import smtplib
from pathlib import Path
from tkinter import ttk
import datetime
import logging
import queue
import os
import tkinter as tk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


from watchdog.events import (
    EVENT_TYPE_CREATED,
    EVENT_TYPE_DELETED,
    EVENT_TYPE_MODIFIED,
    EVENT_TYPE_MOVED
)

# Se genera el archivo .log
absolutepath = os.path.abspath(__file__)
fileDirectory = os.path.dirname(absolutepath)
log = "\\WatchdogFolder.log"

logging.basicConfig(filename= fileDirectory + log,level=logging.INFO)
print(fileDirectory + log)

# Metodo para enviar mails
class SendMail():    
    def send_email(item):
        message = "Nuevo elemento creado: " + item
        subject = "Monitoreo de archivos nuevos"
        message = 'Subject: {}\n\n{}'.format(subject,message)
        
        server = smtplib.SMTP('smtp.gmail.com',587)
        server.starttls()
        server.login('sender@gmail.com', 'contraseña')
        server.sendmail('sender@gmail.com', 'receptor@gmail.com', message)
        server.quit()
        

class ControladorEventos(FileSystemEventHandler):
    def __init__(self, q):
        # Guardar referencia a la cola para poder utilizarla
        # en on_any_event().
        self._q = q
        super().__init__()
    
    def on_any_event(self, event):
        # Determinar el nombre de la operación.
        action = {
            EVENT_TYPE_CREATED: "Archivo generado",
            EVENT_TYPE_DELETED: "Archivo eliminado",
            EVENT_TYPE_MODIFIED: "Archivo modificado",
            EVENT_TYPE_MOVED: "Archivo movido",
        }[event.event_type]
        
        # Si es un movimiento, agregar la ruta de destino.
        if event.event_type == EVENT_TYPE_MOVED:
            action += f" ({event.dest_path})"
        
        # Si se crea un nuevo elemento, envia mail de notificación 
        if event.event_type == EVENT_TYPE_CREATED:   
            SendMail.send_email(Path(event.src_path).name)
            logging.info("Mail enviado a las: " + datetime.now().strftime("%d/%m/%Y - %H:%M:%S"))
            
        # Agregar la información del evento a la cola, para que sea
        # procesada por loop_observer() en el hilo principal.
        # (No es conveniente modificar un control de Tk desde
        # un hilo secundario).
        self._q.put((
            # Nombre del archivo modificado.
            Path(event.src_path).name,
            # Acción ejecutada sobre ese archivo.
            action,
            # Hora en que se ejecuta la acción.
            datetime.datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
        ))
        
def procesador_eventos(observer, q, modtree):
    # Chequear que el observador esté aún corriendo.
    if not observer.is_alive():
        return
    try:
        # Intentar obtener un evento de la cola.
        new_item = q.get_nowait()
    except queue.Empty:
        # Si no hay ninguno, continuar normalmente.
        pass
    else:
        # Si se pudo obtener un evento, agregarlo a la vista de árbol.
        modtree.insert("", 0, text=new_item[0], values=new_item[1:])
             
        # Genera el log
        logging.info(new_item)    
                
    # Volver a chequear dentro de medio segundo (500 ms).
    root.after(500, procesador_eventos, observer, q, modtree)


if __name__=='__main__':
    #Se crea la ventana    
    root = tk.Tk()
    root.config(width=600, height=500)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.title("Registro de modificaciones en tiempo real")
    modtree = ttk.Treeview(columns=("action", "time",))
    modtree.heading("#0", text="Archivo")
    modtree.heading("action", text="Acción")
    modtree.heading("time", text="Fecha y hora")
    modtree.grid(column=0, row=0, sticky="nsew")

    # Observador de eventos de Watchdog.
    observer = Observer()

    # Cola para comunicación entre el observador y la aplicación de Tk.
    q = queue.Queue()
    observer.schedule(ControladorEventos(q), ".", recursive=False)
    observer.start()

    # Programar función que procesa los eventos del observador.
    root.after(1, procesador_eventos, observer, q, modtree)
    root.mainloop()
    observer.stop()
    observer.join()