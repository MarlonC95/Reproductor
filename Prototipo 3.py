import os
import pygame
from pygame import mixer
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
from typing import Optional, Dict, List, Literal
from PIL import Image, ImageTk, ImageFilter
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
import math
import random

# ==================== CONSTANTES ====================
MODOS_REPETICION = ["Ninguno", "Una canción", "Toda la lista"]
TEMAS_PREDEFINIDOS = {
    "Oscuro": {"fondo": "#2E3440", "botones": "#3B4252", "texto": "#E5E9F0", "resaltado": "#88C0D0"},
    "Claro": {"fondo": "#F5F5F5", "botones": "#E0E0E0", "texto": "#212121", "resaltado": "#64B5F6"},
    "Azul": {"fondo": "#0A2463", "botones": "#3E92CC", "texto": "#FFFFFF", "resaltado": "#D8315B"},
    "Verde": {"fondo": "#1B4332", "botones": "#40916C", "texto": "#D8F3DC", "resaltado": "#FF9F1C"}
}

# ==================== PANTALLA DE INICIO ====================
class PantallaInicio:
    def __init__(self, root, al_iniciar):
        self.root = root
        self.al_iniciar = al_iniciar
        self.configurar_ui()

    def configurar_ui(self):
        self.root.title("Yautja-Music")
        self.root.geometry("1000x700")
        self.root.configure(bg='black')

        marco_principal = tk.Frame(self.root, bg='black')
        marco_principal.place(relx=0.5, rely=0.5, anchor='center')

        try:
            ruta_base = os.path.dirname(os.path.abspath(__file__))
            ruta_logo = os.path.join(ruta_base, "assets", "logo.png")
            
            if os.path.exists(ruta_logo):
                img = Image.open(ruta_logo)
                img = img.resize((600, 300), Image.Resampling.LANCZOS)
                self.imagen_logo = ImageTk.PhotoImage(img)
                
                etiqueta_logo = tk.Label(marco_principal, image=self.imagen_logo, bg='black')
                etiqueta_logo.pack(pady=20)
        except Exception as e:
            print(f"Error cargando logo: {e}")

        tk.Label(marco_principal, 
                text="Dep_95", 
                bg='black', 
                fg='white', 
                font=("Arial", 48, "bold")
        ).pack(pady=(0, 10))

        tk.Label(marco_principal, 
                text="Yautja-Music", 
                bg='black', 
                fg='red',
                font=("Arial", 36, "bold")
        ).pack(pady=(0, 40))

        btn_iniciar = tk.Button(marco_principal, 
                              text="ENTRAR", 
                              command=self.iniciar_aplicacion,
                              bg='black', 
                              fg='white', 
                              font=("Arial", 18),
                              relief='flat',
                              bd=0,
                              activebackground='red',
                              activeforeground='white')
        btn_iniciar.pack(pady=20, ipadx=30, ipady=10)

        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def iniciar_aplicacion(self):
        self.al_iniciar()

# ==================== CLASES DEL REPRODUCTOR ====================
class Cancion:
    def __init__(self, titulo: str, artista: str, duracion: float, ruta_archivo: str, genero: str):
        self.titulo = titulo
        self.artista = artista
        self.duracion = duracion
        self.ruta_archivo = ruta_archivo
        self.genero = genero
    
    def __str__(self) -> str:
        return f"{self.titulo} - {self.artista} ({self.duracion:.2f} min)"
    
    def editar(self, nuevo_titulo: str, nuevo_artista: str, nueva_duracion: float, nuevo_genero: str):
        self.titulo = nuevo_titulo
        self.artista = nuevo_artista
        self.duracion = nueva_duracion
        self.genero = nuevo_genero

class NodoCancion:
    def __init__(self, cancion: Cancion):
        self.cancion = cancion
        self.siguiente: Optional['NodoCancion'] = None
        self.anterior: Optional['NodoCancion'] = None

class ListaReproduccion:
    def __init__(self):
        self.cabeza: Optional[NodoCancion] = None
        self.actual: Optional[NodoCancion] = None
        self.reproduciendo = False
        self.modo_repeticion = "Ninguno"
        self.volumen = 0.7
        self.posicion_pausa = 0
        self.fft_data = np.zeros(1024)
        self.audio_lock = threading.Lock()
        self.spectrum_running = True
        self.spectrum_thread = threading.Thread(target=self.generar_datos_espectro)
        self.spectrum_thread.daemon = True
        self.spectrum_thread.start()
    
    def generar_datos_espectro(self):
        while self.spectrum_running:
            if self.reproduciendo:
                try:
                    # Generamos datos de espectro simulados con ritmo
                    freqs = np.arange(1024)
                    
                    # Base de ruido
                    noise = np.random.normal(0, 0.1, 1024)
                    
                    # Picos en diferentes frecuencias
                    peak1 = 50 * np.exp(-((freqs - 200)**2) / (2 * 80**2))
                    peak2 = 70 * np.exp(-((freqs - 500)**2) / (2 * 100**2))
                    peak3 = 30 * np.exp(-((freqs - 800)**2) / (2 * 50**2))
                    
                    # Ritmo basado en el tiempo
                    beat = max(0.1, 0.5 + 0.5 * math.sin(time.time() * 5))
                    
                    # Combinamos todo
                    fft = np.abs(noise + peak1 + peak2 + peak3) * beat
                    
                    with self.audio_lock:
                        self.fft_data = fft
                except Exception as e:
                    print(f"Error en generación de espectro: {e}")
            else:
                # Cuando no hay reproducción, mostramos línea base
                with self.audio_lock:
                    self.fft_data = np.zeros(1024)
            
            time.sleep(0.05)
    
    def obtener_fft(self):
        with self.audio_lock:
            return self.fft_data.copy()
    
    def agregar_cancion(self, cancion: Cancion) -> None:
        nuevo_nodo = NodoCancion(cancion)
        if not self.cabeza:
            self.cabeza = nuevo_nodo
            self.cabeza.siguiente = self.cabeza
            self.cabeza.anterior = self.cabeza
            self.actual = self.cabeza
        else:
            ultimo = self.cabeza.anterior
            ultimo.siguiente = nuevo_nodo
            nuevo_nodo.anterior = ultimo
            nuevo_nodo.siguiente = self.cabeza
            self.cabeza.anterior = nuevo_nodo
    
    def eliminar_cancion(self, titulo: str) -> bool:
        if not self.cabeza:
            return False
        
        if self.cabeza.cancion.titulo == titulo:
            if self.cabeza.siguiente == self.cabeza:
                self.cabeza = None
                self.actual = None
            else:
                ultimo = self.cabeza.anterior
                self.cabeza = self.cabeza.siguiente
                self.cabeza.anterior = ultimo
                ultimo.siguiente = self.cabeza
                if self.actual and self.actual.cancion.titulo == titulo:
                    self.actual = self.cabeza
            return True
        
        temp = self.cabeza
        while True:
            if temp.siguiente.cancion.titulo == titulo:
                temp.siguiente = temp.siguiente.siguiente
                temp.siguiente.anterior = temp
                if self.actual and self.actual.cancion.titulo == titulo:
                    self.actual = temp.siguiente
                return True
            temp = temp.siguiente
            if temp == self.cabeza:
                break
        
        return False
    
    def obtener_canciones(self) -> List[Cancion]:
        canciones = []
        if not self.cabeza:
            return canciones
        
        temp = self.cabeza
        while True:
            canciones.append(temp.cancion)
            temp = temp.siguiente
            if temp == self.cabeza:
                break
        return canciones
    
    def buscar_cancion(self, titulo: str) -> Optional[Cancion]:
        if not self.cabeza:
            return None
        
        temp = self.cabeza
        while True:
            if temp.cancion.titulo == titulo:
                return temp.cancion
            temp = temp.siguiente
            if temp == self.cabeza:
                break
        return None
    
    def reproducir(self, desde_pausa=False) -> None:
        if not self.cabeza or not self.actual:
            return
        
        if not os.path.exists(self.actual.cancion.ruta_archivo):
            messagebox.showerror("Error", f"Archivo no encontrado: {self.actual.cancion.ruta_archivo}")
            return
        
        try:
            mixer.init()
            mixer.music.load(self.actual.cancion.ruta_archivo)
            mixer.music.set_volume(self.volumen)
            
            if desde_pausa and self.posicion_pausa > 0:
                mixer.music.play(start=self.posicion_pausa)
            else:
                mixer.music.play()
                self.posicion_pausa = 0
                
            self.reproduciendo = True
            mixer.music.set_endevent(pygame.USEREVENT)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo reproducir: {e}")
    
    def manejar_fin(self):
        if self.modo_repeticion == "Una canción":
            self.reproducir()
        elif self.modo_repeticion == "Toda la lista":
            self.siguiente()
        else:
            self.reproduciendo = False
    
    def siguiente(self) -> None:
        if not self.cabeza or not self.actual:
            return
        self.actual = self.actual.siguiente
        self.posicion_pausa = 0
        self.reproducir()
    
    def anterior(self) -> None:
        if not self.cabeza or not self.actual:
            return
        self.actual = self.actual.anterior
        self.posicion_pausa = 0
        self.reproducir()
    
    def pausar(self) -> None:
        if self.reproduciendo:
            self.posicion_pausa = mixer.music.get_pos() / 1000
            mixer.music.pause()
            self.reproduciendo = False
    
    def reanudar(self) -> None:
        if not self.reproduciendo and self.actual:
            if self.posicion_pausa > 0:
                self.reproducir(desde_pausa=True)
            else:
                mixer.music.unpause()
            self.reproduciendo = True
    
    def detener(self) -> None:
        if mixer.get_init():
            mixer.music.stop()
            self.reproduciendo = False
            self.posicion_pausa = 0
    
    def cambiar_modo_repeticion(self) -> str:
        indice_actual = MODOS_REPETICION.index(self.modo_repeticion)
        nuevo_indice = (indice_actual + 1) % len(MODOS_REPETICION)
        self.modo_repeticion = MODOS_REPETICION[nuevo_indice]
        return self.modo_repeticion
    
    def seleccionar_cancion(self, cancion: Cancion) -> None:
        if not self.cabeza:
            return
        
        temp = self.cabeza
        while True:
            if temp.cancion.titulo == cancion.titulo:
                self.actual = temp
                self.posicion_pausa = 0
                self.reproducir()
                break
            temp = temp.siguiente
            if temp == self.cabeza:
                break

class GestorListas:
    def __init__(self):
        self.listas: Dict[str, ListaReproduccion] = {}
        self.lista_actual: Optional[ListaReproduccion] = None
    
    def crear_lista(self, nombre: str) -> bool:
        if nombre in self.listas:
            return False
        self.listas[nombre] = ListaReproduccion()
        return True
    
    def seleccionar_lista(self, nombre: str) -> bool:
        if nombre not in self.listas:
            return False
        self.lista_actual = self.listas[nombre]
        return True
    
    def eliminar_lista(self, nombre: str) -> bool:
        if nombre not in self.listas:
            return False
        
        if self.lista_actual == self.listas[nombre]:
            self.lista_actual.detener()
            self.lista_actual = None
        
        del self.listas[nombre]
        return True
    
    def obtener_nombres_listas(self) -> List[str]:
        return list(self.listas.keys())

# ==================== INTERFAZ PRINCIPAL ====================
class ReproductorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.gestor = GestorListas()
        self.tema = TEMAS_PREDEFINIDOS["Oscuro"].copy()
        self.mini_player = None
        self.mini_player_visible = False
        self.animacion_activa = True
        self.animacion_alpha = 1.0
        
        self._configurar_ui()
        self._configurar_eventos()
        self._configurar_menu()
        self._crear_mini_player()
        self.actualizar_animacion()
        self._actualizar_visualizador()
    
    def _configurar_ui(self):
        self.root.title("Yautja-Music")
        self._actualizar_tema()
        
        # Marco principal
        self.marco_principal = tk.Frame(self.root, bg=self.tema["fondo"])
        self.marco_principal.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Título
        self.etiqueta_titulo = tk.Label(
            self.marco_principal,
            text="Reproductor de Música",
            bg=self.tema["fondo"],
            fg=self.tema["texto"],
            font=("Arial", 24, "bold")
        )
        self.etiqueta_titulo.pack(pady=(10, 20))
        
        # Panel de listas
        self._configurar_panel_listas()
        
        # Panel de canciones
        self._configurar_panel_canciones()
        
        # Visualizador de espectro
        self._configurar_visualizador()
        
        # Controles
        self._configurar_controles()
        
        # Barra de estado
        self._configurar_barra_estado()
    
    def _actualizar_tema(self):
        self.root.configure(bg=self.tema["fondo"])
        if hasattr(self, 'marco_principal'):
            self.marco_principal.configure(bg=self.tema["fondo"])
        if hasattr(self, 'etiqueta_titulo'):
            self.etiqueta_titulo.configure(bg=self.tema["fondo"], fg=self.tema["texto"])
        
        estilo = ttk.Style()
        estilo.configure("Treeview", 
            background=self.tema["botones"], 
            fieldbackground=self.tema["botones"], 
            foreground=self.tema["texto"],
            rowheight=25
        )
        estilo.configure("Treeview.Heading", 
            background=self.tema["resaltado"], 
            foreground=self.tema["texto"],
            relief="flat"
        )
        estilo.map("Treeview", background=[("selected", self.tema["resaltado"])])
        
        if self.mini_player and self.mini_player.winfo_exists():
            self.mini_player.configure(bg=self.tema["fondo"])
            for widget in self.mini_player.winfo_children():
                if isinstance(widget, tk.Frame):
                    widget.configure(bg=self.tema["fondo"])
                elif isinstance(widget, tk.Label):
                    widget.configure(bg=self.tema["fondo"], fg=self.tema["texto"])
                elif isinstance(widget, tk.Button):
                    if widget['text'] in ["⏮", "⏭"]:
                        widget.configure(bg=self.tema["botones"], fg=self.tema["texto"])
                    elif widget['text'] in ["▶", "⏸"]:
                        widget.configure(bg=self.tema["resaltado"], fg=self.tema["fondo"])
    
    def _configurar_visualizador(self):
        self.marco_visualizador = tk.Frame(self.marco_principal, bg=self.tema["fondo"], height=150)
        self.marco_visualizador.pack(fill=tk.X, pady=(10, 0))
        
        self.fig = Figure(figsize=(8, 2), dpi=100, facecolor=self.tema["fondo"])
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(self.tema["fondo"])
        self.line, = self.ax.plot(np.random.rand(1024), color=self.tema["resaltado"])
        self.ax.set_ylim(0, 100)
        self.ax.axis('off')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.marco_visualizador)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _actualizar_visualizador(self):
        if hasattr(self, 'canvas') and self.gestor.lista_actual:
            fft_data = self.gestor.lista_actual.obtener_fft()
            if len(fft_data) > 0:
                self.line.set_ydata(fft_data)
                self.ax.set_ylim(0, max(100, np.max(fft_data)*1.1))
                self.canvas.draw()
        
        self.root.after(50, self._actualizar_visualizador)
    
    def _configurar_panel_listas(self):
        marco = tk.Frame(self.marco_principal, bg=self.tema["botones"], padx=10, pady=10)
        marco.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(marco, text="Listas de Reproducción:", 
                bg=self.tema["botones"], fg=self.tema["texto"], font=("Arial", 12)).pack(side=tk.LEFT)
        
        self.combo_listas = ttk.Combobox(marco, state="readonly")
        self.combo_listas.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
        self.combo_listas.bind("<<ComboboxSelected>>", self.cambiar_lista)
        
        btn_nueva = tk.Button(marco, text="Nueva", command=self.nueva_lista,
                            bg=self.tema["resaltado"], fg=self.tema["texto"], relief=tk.FLAT)
        btn_nueva.pack(side=tk.LEFT, padx=5)
        
        btn_eliminar = tk.Button(marco, text="Eliminar", command=self.eliminar_lista,
                                bg=self.tema["resaltado"], fg=self.tema["texto"], relief=tk.FLAT)
        btn_eliminar.pack(side=tk.LEFT, padx=5)
    
    def _configurar_panel_canciones(self):
        marco = tk.Frame(self.marco_principal, bg=self.tema["fondo"])
        marco.pack(fill=tk.BOTH, expand=True)
        
        # Lista de canciones
        self.lista_canciones = ttk.Treeview(marco, columns=("titulo", "artista", "duracion", "genero"), 
                                          show="headings", selectmode="browse")
        
        # Configurar columnas
        self.lista_canciones.heading("titulo", text="Título")
        self.lista_canciones.heading("artista", text="Artista")
        self.lista_canciones.heading("duracion", text="Duración (min)")
        self.lista_canciones.heading("genero", text="Género")
        
        self.lista_canciones.column("titulo", width=300)
        self.lista_canciones.column("artista", width=250)
        self.lista_canciones.column("duracion", width=120)
        self.lista_canciones.column("genero", width=180)
        
        # Scrollbar
        scroll = ttk.Scrollbar(marco, orient="vertical", command=self.lista_canciones.yview)
        self.lista_canciones.configure(yscrollcommand=scroll.set)
        
        self.lista_canciones.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones de canciones
        marco_botones = tk.Frame(marco, bg=self.tema["fondo"])
        marco_botones.pack(fill=tk.X, pady=(15, 0))
        
        btn_agregar = tk.Button(marco_botones, text="+ Agregar Canción", command=self.agregar_cancion,
                               bg=self.tema["botones"], fg=self.tema["texto"], relief=tk.FLAT,
                               font=("Arial", 10))
        btn_agregar.pack(side=tk.LEFT, padx=5, ipadx=10)
        
        btn_eliminar = tk.Button(marco_botones, text="- Eliminar Canción", command=self.eliminar_cancion,
                                bg=self.tema["botones"], fg=self.tema["texto"], relief=tk.FLAT,
                                font=("Arial", 10))
        btn_eliminar.pack(side=tk.LEFT, padx=5, ipadx=10)
        
        btn_editar = tk.Button(marco_botones, text="✏ Editar", command=self.editar_cancion,
                              bg=self.tema["botones"], fg=self.tema["texto"], relief=tk.FLAT,
                              font=("Arial", 10))
        btn_editar.pack(side=tk.LEFT, padx=5, ipadx=10)
    
    def _configurar_controles(self):
        marco = tk.Frame(self.marco_principal, bg=self.tema["botones"], padx=15, pady=15)
        marco.pack(fill=tk.X, pady=(15, 0))
        
        # Botón de repetición
        self.btn_repetir = tk.Button(marco, text="Repetir: Ninguno", 
                                    command=self.cambiar_repeticion,
                                    bg=self.tema["resaltado"], fg=self.tema["texto"], 
                                    relief=tk.FLAT, font=("Arial", 10))
        self.btn_repetir.pack(side=tk.LEFT, padx=10)
        
        # Controles de reproducción
        btn_anterior = tk.Button(marco, text="⏮", command=self.cancion_anterior,
                                bg=self.tema["botones"], fg=self.tema["texto"], 
                                relief=tk.FLAT, font=("Arial", 14), width=3)
        btn_anterior.pack(side=tk.LEFT, padx=5)
        
        self.btn_play = tk.Button(marco, text="▶", command=self.toggle_reproduccion,
                                 bg=self.tema["resaltado"], fg=self.tema["fondo"], 
                                 relief=tk.FLAT, font=("Arial", 14), width=3)
        self.btn_play.pack(side=tk.LEFT, padx=5)
        
        btn_siguiente = tk.Button(marco, text="⏭", command=self.cancion_siguiente,
                                 bg=self.tema["botones"], fg=self.tema["texto"], 
                                 relief=tk.FLAT, font=("Arial", 14), width=3)
        btn_siguiente.pack(side=tk.LEFT, padx=5)
        
        # Control de volumen
        tk.Label(marco, text="Volumen:", bg=self.tema["botones"], 
                fg=self.tema["texto"], font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))
        
        self.barra_volumen = ttk.Scale(marco, from_=0, to=100, value=70,
                                     command=self.ajustar_volumen, length=200)
        self.barra_volumen.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        # Botón mini player
        btn_mini = tk.Button(marco, text="🗖", command=self.toggle_mini_player,
                           bg=self.tema["botones"], fg=self.tema["texto"], 
                           relief=tk.FLAT, font=("Arial", 14), width=3)
        btn_mini.pack(side=tk.RIGHT, padx=5)
    
    def _configurar_barra_estado(self):
        self.var_estado = tk.StringVar()
        self.var_estado.set("Bienvenido a Yautja-Music")
        
        etiqueta_estado = tk.Label(self.marco_principal, textvariable=self.var_estado, 
                                 bg=self.tema["botones"], fg=self.tema["texto"], 
                                 anchor=tk.W, font=("Arial", 10))
        etiqueta_estado.pack(fill=tk.X, pady=(15, 0), ipady=5)
    
    def _configurar_menu(self):
        barra_menu = tk.Menu(self.root)
        
        # Menú Apariencia
        menu_apariencia = tk.Menu(barra_menu, tearoff=0)
        menu_apariencia.add_command(label="Cambiar color de fondo...", command=self.cambiar_color_fondo)
        menu_apariencia.add_command(label="Cambiar color de botones...", command=self.cambiar_color_botones)
        menu_apariencia.add_command(label="Cambiar color de texto...", command=self.cambiar_color_texto)
        menu_apariencia.add_command(label="Cambiar color resaltado...", command=self.cambiar_color_resaltado)
        menu_apariencia.add_separator()
        
        # Submenú Temas
        menu_temas = tk.Menu(menu_apariencia, tearoff=0)
        for tema in TEMAS_PREDEFINIDOS:
            menu_temas.add_command(label=tema, command=lambda t=tema: self.aplicar_tema(t))
        menu_apariencia.add_cascade(label="Temas predefinidos", menu=menu_temas)
        
        barra_menu.add_cascade(label="Apariencia", menu=menu_apariencia)
        
        # Menú Visualización
        menu_visual = tk.Menu(barra_menu, tearoff=0)
        menu_visual.add_command(label="Mostrar/Ocultar visualizador", command=self.toggle_visualizador)
        menu_visual.add_command(label="Activar/Desactivar animaciones", command=self.toggle_animaciones)
        barra_menu.add_cascade(label="Visualización", menu=menu_visual)
        
        # Menú Ayuda
        menu_ayuda = tk.Menu(barra_menu, tearoff=0)
        menu_ayuda.add_command(label="Acerca de...", command=self.mostrar_acerca_de)
        barra_menu.add_cascade(label="Ayuda", menu=menu_ayuda)
        
        self.root.config(menu=barra_menu)
    
    def _configurar_eventos(self):
        self.lista_canciones.bind("<Double-1>", self.seleccionar_cancion)
        self.root.bind("<space>", lambda e: self.toggle_reproduccion())
        self.root.protocol("WM_DELETE_WINDOW", self.al_cerrar)
    
    def toggle_visualizador(self):
        if self.marco_visualizador.winfo_ismapped():
            self.marco_visualizador.pack_forget()
        else:
            self.marco_visualizador.pack(fill=tk.X, pady=(10, 0))
    
    def toggle_animaciones(self):
        self.animacion_activa = not self.animacion_activa
        if self.animacion_activa:
            self.animacion_alpha = 1.0
    
    def actualizar_animacion(self):
        if self.animacion_activa and self.gestor.lista_actual and self.gestor.lista_actual.reproduciendo:
            self.animacion_alpha = 0.5 + (math.sin(time.time() * 5) + 1) / 4
            self.btn_play.config(bg=self._interpolar_color(
                self.tema["resaltado"], 
                self.tema["botones"], 
                self.animacion_alpha
            ))
        
        self.root.after(50, self.actualizar_animacion)
    
    def _interpolar_color(self, color1, color2, alpha):
        def hex_to_rgb(hex_color):
            return tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
        
        def rgb_to_hex(rgb):
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
        c1 = hex_to_rgb(color1)
        c2 = hex_to_rgb(color2)
        r = int(c1[0] * alpha + c2[0] * (1 - alpha))
        g = int(c1[1] * alpha + c2[1] * (1 - alpha))
        b = int(c1[2] * alpha + c2[2] * (1 - alpha))
        return rgb_to_hex((r, g, b))
    
    def toggle_mini_player(self):
        if self.mini_player_visible:
            self.mini_player.withdraw()
            self.mini_player_visible = False
        else:
            self.mini_player.deiconify()
            self.mini_player_visible = True
            self._actualizar_mini_player()
    
    def _crear_mini_player(self):
        self.mini_player = tk.Toplevel(self.root)
        self.mini_player.title("Yautja-Music Mini")
        self.mini_player.geometry("400x100+{}+{}".format(
            self.root.winfo_x() + 50,
            self.root.winfo_y() + 50
        ))
        self.mini_player.protocol("WM_DELETE_WINDOW", self.toggle_mini_player)
        self.mini_player.attributes("-topmost", True)
        self.mini_player.withdraw()
        
        # Hacer que el mini player sea independiente
        self.mini_player.transient(self.root)
        self.mini_player.overrideredirect(False)
        
        # Barra de título
        marco_titulo = tk.Frame(self.mini_player, bg=self.tema["resaltado"], height=25)
        marco_titulo.pack(fill=tk.X)
        
        tk.Label(marco_titulo, text="Yautja-Music Mini", 
                bg=self.tema["resaltado"], fg=self.tema["texto"],
                font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        btn_cerrar = tk.Button(marco_titulo, text="✕", command=self.toggle_mini_player,
                             bg=self.tema["resaltado"], fg=self.tema["texto"],
                             relief=tk.FLAT, bd=0)
        btn_cerrar.pack(side=tk.RIGHT, padx=5)
        
        # Contenido
        marco_contenido = tk.Frame(self.mini_player, bg=self.tema["fondo"])
        marco_contenido.pack(fill=tk.BOTH, expand=True)
        
        # Info de la canción
        self.mini_info = tk.Label(marco_contenido, text="No hay canción reproduciéndose",
                                 bg=self.tema["fondo"], fg=self.tema["texto"],
                                 font=("Arial", 10))
        self.mini_info.pack(pady=5)
        
        # Controles
        marco_controles = tk.Frame(marco_contenido, bg=self.tema["fondo"])
        marco_controles.pack(pady=5)
        
        btn_anterior = tk.Button(marco_controles, text="⏮", command=self.cancion_anterior,
                                bg=self.tema["botones"], fg=self.tema["texto"], 
                                relief=tk.FLAT, font=("Arial", 12), width=3)
        btn_anterior.pack(side=tk.LEFT, padx=5)
        
        self.mini_btn_play = tk.Button(marco_controles, text="▶", command=self.toggle_reproduccion,
                                     bg=self.tema["resaltado"], fg=self.tema["fondo"], 
                                     relief=tk.FLAT, font=("Arial", 12), width=3)
        self.mini_btn_play.pack(side=tk.LEFT, padx=5)
        
        btn_siguiente = tk.Button(marco_controles, text="⏭", command=self.cancion_siguiente,
                                bg=self.tema["botones"], fg=self.tema["texto"], 
                                relief=tk.FLAT, font=("Arial", 12), width=3)
        btn_siguiente.pack(side=tk.LEFT, padx=5)
        
        # Hacer la ventana arrastrable
        def start_move(event):
            self.mini_player.x = event.x
            self.mini_player.y = event.y
        
        def stop_move(event):
            self.mini_player.x = None
            self.mini_player.y = None
        
        def do_move(event):
            deltax = event.x - self.mini_player.x
            deltay = event.y - self.mini_player.y
            x = self.mini_player.winfo_x() + deltax
            y = self.mini_player.winfo_y() + deltay
            self.mini_player.geometry(f"+{x}+{y}")
        
        marco_titulo.bind("<ButtonPress-1>", start_move)
        marco_titulo.bind("<ButtonRelease-1>", stop_move)
        marco_titulo.bind("<B1-Motion>", do_move)
    
    def _actualizar_mini_player(self):
        if self.mini_player_visible and self.mini_player.winfo_exists():
            if self.gestor.lista_actual and self.gestor.lista_actual.actual:
                cancion = self.gestor.lista_actual.actual.cancion
                self.mini_info.config(text=f"{cancion.titulo} - {cancion.artista}")
                self.mini_btn_play.config(text="⏸" if self.gestor.lista_actual.reproduciendo else "▶")
            else:
                self.mini_info.config(text="No hay canción reproduciéndose")
                self.mini_btn_play.config(text="▶")
            
            self.root.after(1000, self._actualizar_mini_player)
    
    def cambiar_color_fondo(self):
        color = colorchooser.askcolor(title="Elige color de fondo", initialcolor=self.tema["fondo"])[1]
        if color:
            self.tema["fondo"] = color
            self._actualizar_tema()
    
    def cambiar_color_botones(self):
        color = colorchooser.askcolor(title="Elige color de botones", initialcolor=self.tema["botones"])[1]
        if color:
            self.tema["botones"] = color
            self._actualizar_tema()
    
    def cambiar_color_texto(self):
        color = colorchooser.askcolor(title="Elige color de texto", initialcolor=self.tema["texto"])[1]
        if color:
            self.tema["texto"] = color
            self._actualizar_tema()
    
    def cambiar_color_resaltado(self):
        color = colorchooser.askcolor(title="Elige color resaltado", initialcolor=self.tema["resaltado"])[1]
        if color:
            self.tema["resaltado"] = color
            self._actualizar_tema()
    
    def aplicar_tema(self, tema: str):
        if tema in TEMAS_PREDEFINIDOS:
            self.tema = TEMAS_PREDEFINIDOS[tema].copy()
            self._actualizar_tema()
    
    def cambiar_lista(self, event=None):
        lista_seleccionada = self.combo_listas.get()
        if lista_seleccionada:
            self.gestor.seleccionar_lista(lista_seleccionada)
            self.actualizar_canciones()
            self.var_estado.set(f"Lista activa: {lista_seleccionada}")
    
    def actualizar_listas(self):
        listas = self.gestor.obtener_nombres_listas()
        self.combo_listas["values"] = listas
        if listas:
            self.combo_listas.current(0)
            self.cambiar_lista()
    
    def actualizar_canciones(self):
        self.lista_canciones.delete(*self.lista_canciones.get_children())
        if self.gestor.lista_actual:
            for cancion in self.gestor.lista_actual.obtener_canciones():
                self.lista_canciones.insert("", "end", values=(
                    cancion.titulo, 
                    cancion.artista, 
                    f"{cancion.duracion:.2f}",
                    cancion.genero
                ))
    
    def nueva_lista(self):
        nombre = simpledialog.askstring("Nueva Lista", "Nombre de la lista:")
        if nombre:
            if self.gestor.crear_lista(nombre):
                self.actualizar_listas()
                self.var_estado.set(f"Lista '{nombre}' creada")
            else:
                messagebox.showerror("Error", "Ya existe una lista con ese nombre")
    
    def eliminar_lista(self):
        lista = self.combo_listas.get()
        if lista and messagebox.askyesno("Confirmar", f"¿Eliminar lista '{lista}'?"):
            if self.gestor.eliminar_lista(lista):
                self.actualizar_listas()
                self.var_estado.set(f"Lista '{lista}' eliminada")
    
    def agregar_cancion(self):
        if not self.gestor.lista_actual:
            messagebox.showwarning("Advertencia", "Selecciona una lista primero")
            return
        
        archivo = filedialog.askopenfilename(
            title="Seleccionar canción",
            filetypes=[("Archivos de audio", "*.mp3 *.wav *.ogg"), ("Todos los archivos", "*.*")]
        )
        
        if archivo:
            ventana_meta = tk.Toplevel(self.root)
            ventana_meta.title("Información de la canción")
            ventana_meta.configure(bg=self.tema["fondo"])
            ventana_meta.resizable(False, False)
            ventana_meta.geometry(f"400x300+{self.root.winfo_x()+250}+{self.root.winfo_y()+150}")
            ventana_meta.grid_columnconfigure(1, weight=1)
            
            campos = [
                ("Título:", os.path.basename(archivo).split('.')[0]),
                ("Artista:", "Desconocido"),
                ("Duración (min):", "0.0"),
                ("Género:", "No especificado")
            ]
            
            self.entradas = []
            for i, (texto, valor_inicial) in enumerate(campos):
                tk.Label(ventana_meta, text=texto, bg=self.tema["fondo"], 
                        fg=self.tema["texto"], font=("Arial", 10)).grid(
                            row=i, column=0, padx=10, pady=5, sticky="e")
                
                entrada = tk.Entry(ventana_meta, font=("Arial", 10))
                entrada.insert(0, valor_inicial)
                entrada.grid(row=i, column=1, padx=10, pady=5, sticky="we")
                self.entradas.append(entrada)
            
            marco_botones = tk.Frame(ventana_meta, bg=self.tema["fondo"])
            marco_botones.grid(row=len(campos), column=0, columnspan=2, pady=15)
            
            btn_guardar = tk.Button(
                marco_botones, text="Guardar", command=lambda: self.guardar_cancion(archivo, ventana_meta),
                bg=self.tema["botones"], fg=self.tema["texto"], relief=tk.FLAT,
                font=("Arial", 10), width=10
            )
            btn_guardar.pack(side=tk.LEFT, padx=10)
            
            btn_cancelar = tk.Button(
                marco_botones, text="Cancelar", command=ventana_meta.destroy,
                bg=self.tema["botones"], fg=self.tema["texto"], relief=tk.FLAT,
                font=("Arial", 10), width=10
            )
            btn_cancelar.pack(side=tk.LEFT, padx=10)
            
            ventana_meta.grab_set()
            ventana_meta.transient(self.root)
            ventana_meta.wait_window(ventana_meta)
    
    def guardar_cancion(self, archivo, ventana):
        try:
            titulo = self.entradas[0].get().strip()
            artista = self.entradas[1].get().strip()
            duracion = float(self.entradas[2].get().strip())
            genero = self.entradas[3].get().strip()
            
            if not titulo:
                messagebox.showerror("Error", "El título no puede estar vacío")
                return
            
            cancion = Cancion(titulo, artista, duracion, archivo, genero)
            self.gestor.lista_actual.agregar_cancion(cancion)
            self.actualizar_canciones()
            self.var_estado.set(f"Canción '{titulo}' agregada")
            ventana.destroy()
        except ValueError:
            messagebox.showerror("Error", "La duración debe ser un número válido")
    
    def editar_cancion(self):
        if not self.gestor.lista_actual:
            messagebox.showwarning("Advertencia", "No hay lista activa seleccionada")
            return
        
        seleccion = self.lista_canciones.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Selecciona una canción para editar")
            return
        
        try:
            valores = self.lista_canciones.item(seleccion[0])["values"]
            if not valores or len(valores) < 4:
                messagebox.showerror("Error", "Datos de canción incompletos")
                return
            
            titulo_actual = valores[0]
            cancion = self.gestor.lista_actual.buscar_cancion(titulo_actual)
            
            if not cancion:
                messagebox.showerror("Error", "Canción no encontrada en la lista")
                return
            
            ventana_edicion = tk.Toplevel(self.root)
            ventana_edicion.title("Editar canción")
            ventana_edicion.configure(bg=self.tema["fondo"])
            ventana_edicion.resizable(False, False)
            ventana_edicion.geometry(f"400x300+{self.root.winfo_x()+250}+{self.root.winfo_y()+150}")
            ventana_edicion.grid_columnconfigure(1, weight=1)
            
            campos = [
                ("Título:", cancion.titulo),
                ("Artista:", cancion.artista),
                ("Duración (min):", str(cancion.duracion)),
                ("Género:", cancion.genero)
            ]
            
            self.entradas_edicion = []
            for i, (texto, valor_inicial) in enumerate(campos):
                tk.Label(ventana_edicion, text=texto, bg=self.tema["fondo"], 
                        fg=self.tema["texto"], font=("Arial", 10)).grid(
                            row=i, column=0, padx=10, pady=5, sticky="e")
                
                entrada = tk.Entry(ventana_edicion, font=("Arial", 10))
                entrada.insert(0, valor_inicial)
                entrada.grid(row=i, column=1, padx=10, pady=5, sticky="we")
                self.entradas_edicion.append(entrada)
            
            marco_botones = tk.Frame(ventana_edicion, bg=self.tema["fondo"])
            marco_botones.grid(row=len(campos), column=0, columnspan=2, pady=15)
            
            btn_guardar = tk.Button(
                marco_botones, text="Guardar cambios", command=lambda: self.guardar_edicion(cancion, ventana_edicion),
                bg=self.tema["botones"], fg=self.tema["texto"], relief=tk.FLAT,
                font=("Arial", 10), width=15
            )
            btn_guardar.pack(side=tk.LEFT, padx=10)
            
            btn_cancelar = tk.Button(
                marco_botones, text="Cancelar", command=ventana_edicion.destroy,
                bg=self.tema["botones"], fg=self.tema["texto"], relief=tk.FLAT,
                font=("Arial", 10), width=15
            )
            btn_cancelar.pack(side=tk.LEFT, padx=10)
            
            ventana_edicion.grab_set()
            ventana_edicion.transient(self.root)
            ventana_edicion.wait_window(ventana_edicion)
            
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al editar: {str(e)}")
    
    def guardar_edicion(self, cancion, ventana):
        try:
            nuevo_titulo = self.entradas_edicion[0].get().strip()
            nuevo_artista = self.entradas_edicion[1].get().strip()
            nueva_duracion = float(self.entradas_edicion[2].get().strip())
            nuevo_genero = self.entradas_edicion[3].get().strip()
            
            if not nuevo_titulo:
                messagebox.showerror("Error", "El título no puede estar vacío")
                return
            
            cancion.editar(nuevo_titulo, nuevo_artista, nueva_duracion, nuevo_genero)
            self.actualizar_canciones()
            self.var_estado.set(f"Canción '{nuevo_titulo}' actualizada")
            ventana.destroy()
        except ValueError:
            messagebox.showerror("Error", "La duración debe ser un número válido")
    
    def eliminar_cancion(self):
        if not self.gestor.lista_actual:
            return
        
        seleccion = self.lista_canciones.selection()
        if not seleccion:
            return
        
        titulo = self.lista_canciones.item(seleccion[0])["values"][0]
        if messagebox.askyesno("Confirmar", f"¿Eliminar la canción '{titulo}'?"):
            if self.gestor.lista_actual.eliminar_cancion(titulo):
                self.actualizar_canciones()
                self.var_estado.set(f"Canción '{titulo}' eliminada")
    
    def toggle_reproduccion(self):
        if not self.gestor.lista_actual:
            return
        
        if self.gestor.lista_actual.reproduciendo:
            self.gestor.lista_actual.pausar()
            self.btn_play.config(text="▶")
            if hasattr(self, 'mini_btn_play'):
                self.mini_btn_play.config(text="▶")
        else:
            if not self.gestor.lista_actual.actual and self.gestor.lista_actual.cabeza:
                self.gestor.lista_actual.actual = self.gestor.lista_actual.cabeza
            
            if self.gestor.lista_actual.posicion_pausa > 0:
                self.gestor.lista_actual.reanudar()
            else:
                self.gestor.lista_actual.reproducir()
                
            self.btn_play.config(text="⏸")
            if hasattr(self, 'mini_btn_play'):
                self.mini_btn_play.config(text="⏸")
            
            if self.gestor.lista_actual.actual:
                cancion = self.gestor.lista_actual.actual.cancion
                self.var_estado.set(f"Reproduciendo: {cancion.titulo} - {cancion.artista}")
                if hasattr(self, 'mini_info'):
                    self.mini_info.config(text=f"{cancion.titulo} - {cancion.artista}")
    
    def cancion_siguiente(self):
        if self.gestor.lista_actual:
            self.gestor.lista_actual.siguiente()
            self.btn_play.config(text="⏸")
            if hasattr(self, 'mini_btn_play'):
                self.mini_btn_play.config(text="⏸")
            
            if self.gestor.lista_actual.actual:
                cancion = self.gestor.lista_actual.actual.cancion
                self.var_estado.set(f"Reproduciendo: {cancion.titulo} - {cancion.artista}")
                if hasattr(self, 'mini_info'):
                    self.mini_info.config(text=f"{cancion.titulo} - {cancion.artista}")
    
    def cancion_anterior(self):
        if self.gestor.lista_actual:
            self.gestor.lista_actual.anterior()
            self.btn_play.config(text="⏸")
            if hasattr(self, 'mini_btn_play'):
                self.mini_btn_play.config(text="⏸")
            
            if self.gestor.lista_actual.actual:
                cancion = self.gestor.lista_actual.actual.cancion
                self.var_estado.set(f"Reproduciendo: {cancion.titulo} - {cancion.artista}")
                if hasattr(self, 'mini_info'):
                    self.mini_info.config(text=f"{cancion.titulo} - {cancion.artista}")
    
    def seleccionar_cancion(self, event):
        if not self.gestor.lista_actual:
            return
        
        seleccion = self.lista_canciones.selection()
        if seleccion:
            valores = self.lista_canciones.item(seleccion[0])["values"]
            if valores:
                titulo = valores[0]
                canciones = self.gestor.lista_actual.obtener_canciones()
                for cancion in canciones:
                    if cancion.titulo == titulo:
                        self.gestor.lista_actual.seleccionar_cancion(cancion)
                        self.btn_play.config(text="⏸")
                        if hasattr(self, 'mini_btn_play'):
                            self.mini_btn_play.config(text="⏸")
                        self.var_estado.set(f"Reproduciendo: {cancion.titulo} - {cancion.artista}")
                        if hasattr(self, 'mini_info'):
                            self.mini_info.config(text=f"{cancion.titulo} - {cancion.artista}")
                        break
    
    def cambiar_repeticion(self):
        if self.gestor.lista_actual:
            modo = self.gestor.lista_actual.cambiar_modo_repeticion()
            self.btn_repetir.config(text=f"Repetir: {modo}")
            self.var_estado.set(f"Modo de repetición: {modo}")
    
    def ajustar_volumen(self, valor):
        if self.gestor.lista_actual:
            volumen = float(valor) / 100
            self.gestor.lista_actual.volumen = volumen
            if mixer.get_init():
                mixer.music.set_volume(volumen)
    
    def verificar_eventos(self):
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT:
                if self.gestor.lista_actual:
                    self.gestor.lista_actual.manejar_fin()
                    
                    if self.gestor.lista_actual.actual:
                        cancion = self.gestor.lista_actual.actual.cancion
                        self.var_estado.set(f"Reproduciendo: {cancion.titulo} - {cancion.artista}")
                        if hasattr(self, 'mini_info'):
                            self.mini_info.config(text=f"{cancion.titulo} - {cancion.artista}")
        
        self.root.after(100, self.verificar_eventos)
    
    def mostrar_acerca_de(self):
        messagebox.showinfo("Acerca de", "Yautja-Music\nVersión 2.0\n\nDesarrollado por:\n\nMarlon Celis\n\nTodos los derechos reservados\n\nDedicado a mi mami y mi novia")
    def al_cerrar(self):
        if self.gestor.lista_actual:
            self.gestor.lista_actual.detener()
            self.gestor.lista_actual.spectrum_running = False
        mixer.quit()
        if self.mini_player and self.mini_player.winfo_exists():
            self.mini_player.destroy()
        self.root.destroy()

# ==================== INICIO DE LA APLICACIÓN ====================

pygame.init()
mixer.init()
    
root = tk.Tk()
    
def mostrar_reproductor():
    for widget in root.winfo_children():
        widget.destroy()
        
    style = ttk.Style()
    style.theme_use("clam")
        
    app = ReproductorApp(root)
    app.verificar_eventos()

pantalla_inicio = PantallaInicio(root, mostrar_reproductor)
    
root.mainloop()
pygame.quit()