# -*- coding: utf-8 -*-
# runtime.py (VERSION CON INTERFAZ GRAFICA USANDO Tkinter y caracteres ASCII unicamente)
#
# FLUJO: el compilador genera un .json; este programa lo LEE (json.load) y
# ejecuta el juego. Todo lo que el runtime sabe del juego sale de ese JSON.
# Actividad 4 (Snake evolucionado): niveles, nubes, frutas venenosas, power-up
# "No Morir" y formas de dibujo. Todo es opcional: si el JSON no trae la clave
# 'levels' el juego se comporta exactamente como el Snake original.

import sys
import json
import time
import random
# Tkinter es la libreria GUI estandar de Python, compatible con 2.7
import Tkinter as tk
import tkMessageBox # Necesario para el GAME OVER
# Quitamos os y msvcrt ya que la GUI maneja el dibujo y el input
# import os
# import msvcrt 

# En Python 2.7 'basestring' existe (es el tipo comun de str y unicode).
# En Python 3 no existe; este bloque evita el aviso del editor (Pylance) y
# no cambia nada al ejecutar con Python 2.7.
try:
    basestring
except NameError:
    basestring = str


class Juego:
    # Segundos que pasan, tras terminar el efecto "No Morir", antes de que
    # aparezca otra estrella en el mapa.
    INTERVALO_ESTRELLA = 10
    # Colores de las entidades nuevas de Snake
    COLOR_VENENO = '#9B30FF'
    COLOR_ESTRELLA = '#FFD700'
    # Colores de la cola en el nivel Nyan Cat (se reparten con el operador %)
    ARCOIRIS = ['#FF0000', '#FF8C00', '#FFFF00', '#00FF00', '#00BFFF', '#8A2BE2']
    def tanks_celda_libre(self, x, y, w=3, h=3):
        if not (0 <= x <= self.ancho - w and 0 <= y <= self.alto - h):
            return False
        for dy in range(h):
            for dx in range(w):
                if self.grid[y + dy][x + dx] != 0:
                    return False
        return True

    def tanks_crear_muros(self):
        # Limpiamos primero por seguridad
        for y in range(self.alto):
            for x in range(self.ancho):
                self.grid[y][x] = 0

        # Coordenadas (x0, y0, ancho, alto, tipo) de bloques tácticos estilo arena clásica
        # '#B22222' = Ladrillo destructible | '#A9A9A9' = Acero indestructible
        bloques = [
            # Pilares verticales superiores (ladrillo)
            (5, 7, 2, 5, '#B22222'),   (12, 7, 2, 5, '#B22222'),
            (22, 7, 2, 5, '#B22222'),  (29, 7, 2, 5, '#B22222'),

            # Coberturas centrales (acero en los flancos, ladrillo destructible en el medio)
            (4, 16, 3, 2, '#A9A9A9'),  (11, 16, 4, 2, '#B22222'),
            (17, 16, 2, 2, '#A9A9A9'), # Núcleo central de acero
            (21, 16, 4, 2, '#B22222'), (29, 16, 3, 2, '#A9A9A9'),

            # Pilares inferiores (cobertura cerca del jugador)
            (5, 23, 2, 5, '#B22222'),   (12, 23, 2, 5, '#B22222'),
            (22, 23, 2, 5, '#B22222'),  (29, 23, 2, 5, '#B22222'),

            # Pequeño búnker protector frente al spawn del jugador (ladrillo)
            (15, 29, 6, 1, '#B22222'),
            (15, 30, 1, 2, '#B22222'),
            (20, 30, 1, 2, '#B22222'),
        ]

        for bx, by, bw, bh, color in bloques:
            for dy in range(bh):
                for dx in range(bw):
                    if 0 <= by + dy < self.alto and 0 <= bx + dx < self.ancho:
                        self.grid[by + dy][bx + dx] = color
    def dibujar_martillo(self, x, y):
        t = self.taman_celda
        x0, y0 = x * t, y * t
        # Mango vertical (marrón/amarillo oscuro)
        self.canvas.create_rectangle(
            x0 + t * 0.40, y0 + t * 0.35,
            x0 + t * 0.60, y0 + t * 0.90,
            fill='#D2691E', outline=''
        )
        # Cabeza del martillo horizontal (gris metálico / naranja)
        self.canvas.create_rectangle(
            x0 + t * 0.15, y0 + t * 0.12,
            x0 + t * 0.85, y0 + t * 0.40,
            fill='#FF8C00', outline='#FFFFFF'
        )

    def dibujar_escudo(self, x, y):
        t = self.taman_celda
        x0, y0 = x * t, y * t
        # Silueta de escudo heráldico cyan dentro de 1 celda
        puntos = [
            x0 + t * 0.18, y0 + t * 0.15,
            x0 + t * 0.82, y0 + t * 0.15,
            x0 + t * 0.82, y0 + t * 0.55,
            x0 + t * 0.50, y0 + t * 0.88,
            x0 + t * 0.18, y0 + t * 0.55
        ]
        self.canvas.create_polygon(puntos, fill='#00FFFF', outline='#FFFFFF', width=1)
    
    def __init__(self, datos_juego):
        self.datos_juego = datos_juego
        self.tipo_juego = self.datos_juego.get('tipo_juego', 'TETRIS')
        config = self.datos_juego.get('config', {})
        self.ancho = config.get('grid_size', [10, 20])[0]
        self.alto = config.get('grid_size', [10, 20])[1]
        self.grid = [[0 for _ in range(self.ancho)] for _ in range(self.alto)]
        self.puntuacion = 0
        self.juego_terminado = False
        
        # --- Configuracion de la GUI ---
        self.root = tk.Tk()
        self.root.title("BrickScript - " + self.tipo_juego)
        # Configurar la accion al cerrar la ventana ('X' de la barra de titulo)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
        
        self.taman_celda = 25 # Pixeles por celda
        self.ancho_canvas = self.ancho * self.taman_celda
        self.alto_canvas = self.alto * self.taman_celda
        
        # Canvas para dibujar el juego
        self.canvas = tk.Canvas(self.root, width=self.ancho_canvas, height=self.alto_canvas, bg='#111111')
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        # Marco lateral para la puntuacion y controles
        self.marco_score = tk.Frame(self.root, width=150, height=self.alto_canvas, bg='#222222')
        self.marco_score.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        self.label_score = tk.Label(self.marco_score, text="PUNTUACION\n0", bg='#222222', fg='white', font=('Consolas', 16, 'bold'))
        self.label_score.pack(pady=40, padx=10)
        
        # Nota: Se ha eliminado 'Q: Salir' de los controles en pantalla
        self.label_controles = tk.Label(self.marco_score, text="CONTROLES\nFlechas: Mover/Rotar", bg='#222222', fg='gray', font=('Consolas', 10))
        self.label_controles.pack(pady=20, padx=10)

        # Configurar eventos de teclado. Usamos <Key> para capturar cualquier tecla
        self.root.bind('<Key>', self.manejar_input_gui)

# --- NUEVAS VARIABLES PARA BRICK TANKS ---
        if self.tipo_juego == 'TANKS':
            # 1. Cámara alejada: grid amplio de 36x36 con celdas de 18px
            self.taman_celda = 18
            self.ancho = 36
            self.alto = 36
            self.grid = [[0 for _ in range(self.ancho)] for _ in range(self.alto)]
            self.ancho_canvas = self.ancho * self.taman_celda
            self.alto_canvas = self.alto * self.taman_celda
            self.canvas.config(width=self.ancho_canvas, height=self.alto_canvas)    

            self.velocidad_gravedad = 0.25   # Necesario para que el game_loop no falle
            self.score = 0
            
            # Datos del Jugador (leemos HP del JSON si existe)
            attrs_jugador = self.datos_juego.get('shape_attrs', {}).get('PLAYER_TANK', {})
            self.player_hp = attrs_jugador.get('hp', 3)
            self.player_x = self.ancho // 2
            self.player_y = self.alto - 4
            self.player_direction = 'UP'     # Hacia donde mira (para disparar)
            
            # Listas de entidades en pantalla
            self.bullets = []                # {"x": X, "y": Y, "dir": DIR, "owner": "PLAYER"/"ENEMY"}
            self.enemies = []                # Tanques enemigos activos
            self.powerups_activos = []       # Martillos y escudos en el mapa
            
            # Estado del Final Boss
            self.boss_active = False
            self.boss_x = (self.ancho - 5) // 2
            self.boss_y = 1
            self.boss_dir = 1
            attrs_boss = self.datos_juego.get('shape_attrs', {}).get('FINAL_BOSS', {})
            self.boss_hp = attrs_boss.get('hp', 20)
            
            # Actualizamos el texto de controles en el panel lateral
            self.label_controles.config(text="CONTROLES\nFlechas: Mover\nEspacio: Disparar")

        if self.tipo_juego == 'TETRIS':
            self.pieza_actual = None
            self.pieza_x, self.pieza_y, self.pieza_rotacion = 0, 0, 0
            self.velocidad_gravedad = 0.4
            # --- Atributos dinamicos leidos del JSON (COLOR, CHANCE, POWERUP) ---
            self.pieza_color = '#00FFFF'    # color de la pieza activa
            self.pieza_nombre = None        # nombre de la pieza activa
            self.pieza_es_powerup = False
            self.powerup_actual = None
            self.pu_estado = {}             # contadores por power-up
        
        if self.tipo_juego == 'SNAKE':
            self.serpiente_cuerpo = []
            self.serpiente_direccion = (1, 0)
            self.posicion_comida = None
            self.velocidad_gravedad = 0.15      # 150 ms: igual que el Snake original
            # --- Actividad 4: se leen del JSON (clave 'levels', opcional) ---
            # 'or [...]' = retrocompatibilidad: sin LEVELS el juego es solo BABY
            # y NO cambia la velocidad (no trae 'speed').
            self.niveles = self.datos_juego.get('levels') or [{'nombre': 'BABY'}]
            self.nivel_idx = 0
            self.nubes = []                     # lista de celdas (x, y)
            self.venenos = []                   # frutas venenosas
            self.estrella = None                # fruta del power-up No Morir
            self.penalizacion_veneno = 0
            self.duracion_invul = 0
            self.modo_nyan = False
            # "Manejador de estados": NORMAL <-> INVULNERABLE
            self.estado = 'NORMAL'
            self.t_fin_invul = 0                # hora (time.time()) en que termina
            self.t_proxima_estrella = 0
            # Atributos de la serpiente (SHAPE PIXEL) leidos del JSON
            atributos_serpiente = self.datos_juego.get('shape_attrs', {}).get('PIXEL', {})
            self.forma_serpiente = atributos_serpiente.get('form', 'RECTANGULAR')
            self.color_serpiente = atributos_serpiente.get('color')   # None = color original
            # Panel lateral con el nivel (solo si el juego define varios niveles)
            self.label_nivel = None
            if len(self.niveles) > 1:
                self.label_nivel = tk.Label(self.marco_score, text="", bg='#222222', fg='#FFD700', font=('Consolas', 11, 'bold'))
                self.label_nivel.pack(pady=10, padx=10)
                self.label_controles.config(text="CONTROLES\nFlechas: Mover\n1/2/3: Cambiar nivel")
        
        self.timer_gravedad = 0
        self.frame_ms = 25      # el loop de dibujo corre cada 25 ms (antes 50)
        self.ejecutar_evento('ON_START')
        if self.tipo_juego == 'SNAKE':
            # Despues de ON_START: asi la serpiente ya existe y las nubes
            # no pueden nacer encima de ella.
            self.aplicar_nivel(0)
        self.timer_id = None # Para controlar el loop de Tkinter
        if self.tipo_juego == 'TANKS':
            self.tanks_crear_muros()

    def run(self):
        # Inicia el ciclo principal de juego de Tkinter
        self.root.after(self.frame_ms, self.game_loop) 
        self.root.mainloop() 

    def game_loop(self):
        if self.juego_terminado:
            self.mostrar_game_over()
            return

        # Logica de TICK/Gravedad
        # El loop se ejecuta cada frame_ms (25 ms). Acumulamos el tiempo y,
        # cuando llega a la velocidad del nivel, se dispara ON_TICK.
        # (+ 0.0001 evita errores de redondeo de los decimales)
        self.timer_gravedad += self.frame_ms / 1000.0
        if self.timer_gravedad + 0.0001 >= self.velocidad_gravedad:
            self.timer_gravedad = 0
            self.ejecutar_evento('ON_TICK')

        # El timer del power-up se revisa en CADA frame (no solo en cada tick)
        # para que la cuenta regresiva sea exacta sin importar la velocidad.
        if self.tipo_juego == 'SNAKE':
            self.snake_actualizar_estado()
        elif self.tipo_juego == 'TANKS':
            self.tanks_actualizar_estado()    

        self.dibujar()

        # Programa el siguiente ciclo de juego
        self.timer_id = self.root.after(self.frame_ms, self.game_loop)
        
    def cerrar_ventana(self):
        # Detiene el loop de juego de forma segura
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.root.destroy()
        sys.exit(0)


    def manejar_input_gui(self, event):
        key = event.keysym.upper()
        
        # La opcion de salir con 'Q' ha sido eliminada.
        
        # Mapeo de teclas de flecha
        if self.tipo_juego == 'TETRIS':
            if key == 'UP': self.ejecutar_evento('ON_KEY_UP')
            elif key == 'DOWN': self.ejecutar_evento('ON_KEY_DOWN')
            elif key == 'LEFT': self.ejecutar_evento('ON_KEY_LEFT')
            elif key == 'RIGHT': self.ejecutar_evento('ON_KEY_RIGHT')
        elif self.tipo_juego == 'SNAKE':
            # Llamamos a las funciones internas para Snake
            if key == 'UP': self.snake_cambiar_direccion('UP')
            elif key == 'DOWN': self.snake_cambiar_direccion('DOWN')
            elif key == 'LEFT': self.snake_cambiar_direccion('LEFT')
            elif key == 'RIGHT': self.snake_cambiar_direccion('RIGHT')
            elif key in ('1', '2', '3') and len(self.niveles) > 1:
                # Atajo de prueba: salta directamente al nivel 1, 2 o 3
                if int(key) - 1 < len(self.niveles):
                    self.aplicar_nivel(int(key) - 1)
        def manejar_input_gui(self, event):
            key = event.keysym.upper()

        # Mapeo de teclas de flecha
        if self.tipo_juego == 'TETRIS':
            if key == 'UP': self.ejecutar_evento('ON_KEY_UP')
            elif key == 'DOWN': self.ejecutar_evento('ON_KEY_DOWN')
            elif key == 'LEFT': self.ejecutar_evento('ON_KEY_LEFT')
            elif key == 'RIGHT': self.ejecutar_evento('ON_KEY_RIGHT')
            
        elif self.tipo_juego == 'SNAKE':
            # Llamamos a las funciones internas para Snake
            if key == 'UP': self.snake_cambiar_direccion('UP')
            elif key == 'DOWN': self.snake_cambiar_direccion('DOWN')
            elif key == 'LEFT': self.snake_cambiar_direccion('LEFT')
            elif key == 'RIGHT': self.snake_cambiar_direccion('RIGHT')
            elif key in ('1', '2', '3') and len(self.niveles) > 1:
                # Atajo de prueba: salta directamente al nivel 1, 2 o 3
                if int(key) - 1 < len(self.niveles):
                    self.aplicar_nivel(int(key) - 1)
                    
        # --- NUEVO BLOQUE PARA TANKS ---
        elif self.tipo_juego == 'TANKS':
            if key == 'UP': self.tanks_mover_jugador(0, -1, 'UP')
            elif key == 'DOWN': self.tanks_mover_jugador(0, 1, 'DOWN')
            elif key == 'LEFT': self.tanks_mover_jugador(-1, 0, 'LEFT')
            elif key == 'RIGHT': self.tanks_mover_jugador(1, 0, 'RIGHT')
            elif key == 'SPACE': self.tanks_disparar_jugador()            

    def tanks_mover_jugador(self, dx, dy, direccion):
        # Si el jugador ya perdió (HP en 0), bloqueamos el movimiento
        if getattr(self, 'player_hp', 0) <= 0:
            return

        # 1. Actualizamos hacia dónde está mirando el cañón del tanque
        self.player_direction = direccion

        # 2. Calculamos la futura posición
        nueva_x = self.player_x + dx
        nueva_y = self.player_y + dy

        # 3. Validamos que no se salga de la pantalla.
        # (Uso 30 porque en tu tanks.brick definiste GAME GRID (30, 30).
        # Restamos 2 porque la matriz del tanque mide 3x3)
        if self.tanks_celda_libre(nueva_x, nueva_y):
            self.player_x = nueva_x
            self.player_y = nueva_y

        # Opcional: Si tienes una función para redibujar la pantalla al instante
        # en tu código de Tetris/Snake, llámala aquí. Suele llamarse self.dibujar() 
        # o self.actualizar_canvas(). Si no la tienes, el Game Loop lo hará solo.
        if hasattr(self, 'dibujar'):
            self.dibujar()

    def tanks_disparar_jugador(self):
        if getattr(self, 'player_hp', 0) <= 0:
            return

        # Que la bala salga justo de la punta del cañón (fuera de la matriz 3x3)
        offsets = {
            'UP':    (1, -1),
            'DOWN':  (1, 3),
            'LEFT':  (-1, 1),
            'RIGHT': (3, 1)
        }
        dx, dy = offsets.get(self.player_direction, (1, -1))
        bx = self.player_x + dx
        by = self.player_y + dy

        if 0 <= bx < self.ancho and 0 <= by < self.alto:
            self.bullets.append({
                "x": bx,
                "y": by,
                "dir": self.player_direction,
                "owner": "PLAYER"
            })

    def tanks_actualizar_estado(self):
        if self.juego_terminado:
            return

        # Inicializar contadores internos si no existen
        if not hasattr(self, 'tanks_tick'):
            self.tanks_tick = 0
            self.shield_until = 0

        self.tanks_tick += 1

        # 1. MOVER BALAS (cada 2 frames = 20 celdas/seg, velocidad arcade ideal)
        if self.tanks_tick % 2 == 0:
            balas_activas = []
            for bala in self.bullets:
                if bala['dir'] == 'UP': bala['y'] -= 1
                elif bala['dir'] == 'DOWN': bala['y'] += 1
                elif bala['dir'] == 'LEFT': bala['x'] -= 1
                elif bala['dir'] == 'RIGHT': bala['x'] += 1

                if not (0 <= bala['x'] < self.ancho and 0 <= bala['y'] < self.alto):
                    continue

                # Colisión de la bala contra muros del mapa
                celda_muro = self.grid[bala['y']][bala['x']]
                if celda_muro != 0:
                    if celda_muro == '#B22222':  # Ladrillo: se destruye
                        self.grid[bala['y']][bala['x']] = 0
                    # Tanto ladrillo como acero ('#A9A9A9') detienen la bala
                    continue

                impacto = False

                # Bala del JUGADOR contra Enemigos y Boss
                if bala['owner'] == 'PLAYER':
                    for enemigo in self.enemies[:]:
                        if enemigo['x'] <= bala['x'] < enemigo['x'] + 3 and enemigo['y'] <= bala['y'] < enemigo['y'] + 3:
                            enemigo['hp'] -= 1
                            impacto = True
                            if enemigo['hp'] <= 0:
                                self.puntuacion += enemigo['points']
                                self.enemies.remove(enemigo)
                            break

                    if not impacto and self.boss_active and self.boss_hp > 0:
                        if self.boss_x <= bala['x'] < self.boss_x + 5 and self.boss_y <= bala['y'] < self.boss_y + 3:
                            self.boss_hp -= 1
                            impacto = True
                            if self.boss_hp <= 0:
                                self.puntuacion += 500
                                self.juego_terminado = True  # ¡Victoria!

                # Bala ENEMIGA contra el Jugador
                elif bala['owner'] == 'ENEMY':
                    if self.player_x <= bala['x'] < self.player_x + 3 and self.player_y <= bala['y'] < self.player_y + 3:
                        impacto = True
                        if time.time() > self.shield_until:
                            self.player_hp -= 1
                            if self.player_hp <= 0:
                                self.juego_terminado = True

                if not impacto:
                    balas_activas.append(bala)
            self.bullets = balas_activas

        # 2. RECOGER POWER-UPS (Martillo / Escudo)
        for pu in self.powerups_activos[:]:
            # Colisión de cajas (Jugador 3x3 vs Power-up 2x2)
            if (abs(self.player_x - pu['x']) < 3 and abs(self.player_y - pu['y']) < 3):
                info_pu = self.datos_juego.get('powerups', {}).get(pu['tipo'], {})
                efecto = info_pu.get('efecto', pu['tipo']).upper()
                if 'REPAIR' in efecto or 'MARTILLO' in efecto:
                    self.player_hp = min(self.player_hp + 1, 5)
                elif 'SHIELD' in efecto or 'ESCUDO' in efecto:
                    self.shield_until = time.time() + 6.0  # 6 segundos de escudo
                self.puntuacion += info_pu.get('puntos', 50)
                self.powerups_activos.remove(pu)

        # 3. APARICIÓN DE ENEMIGOS Y POWER-UPS (mientras no esté el Boss)
        if not self.boss_active:
            # Generar enemigos cada ~2 segundos (80 frames) si hay menos de 4
            if self.tanks_tick % 80 == 0 and len(self.enemies) < 4:
                attrs = self.datos_juego.get('shape_attrs', {})
                candidatos = [k for k, v in attrs.items() if v.get('type') == 'ENEMY']
                if candidatos:
                    tipo_e = random.choice(candidatos)
                    info_e = attrs[tipo_e]
                    spawn_x = random.choice([2, 10, 18, 26, 31])  # Posibles posiciones de spawn
                    if self.tanks_celda_libre(spawn_x, 1, 3, 3):
                        self.enemies.append({
                            'tipo': tipo_e,
                            'x': spawn_x,
                            'y': 1,
                            'dir': 'DOWN',
                            'hp': info_e.get('hp', 1),
                            'points': info_e.get('points', 100)
                        })

            # Generar un Power-up aleatorio cada ~4 segundos (160 frames) en celda libre
            if self.tanks_tick % 160 == 0 and len(self.powerups_activos) < 2:
                pus = list(self.datos_juego.get('powerups', {}).keys()) or ['MARTILLO', 'ESCUDO']
                for _ in range(15):
                    px = random.randint(2, self.ancho - 4)
                    py = random.randint(5, self.alto - 5)
                    if self.tanks_celda_libre(px, py, 1, 1):
                        self.powerups_activos.append({
                            'tipo': random.choice(pus),
                            'x': px,
                            'y': py
                        })
                        break

        # 4. IA DE MOVIMIENTO Y DISPARO ENEMIGO (cada 12 frames)
        if self.tanks_tick % 12 == 0:
            dirs = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
            for e in self.enemies:
                if random.random() < 0.25:
                    e['dir'] = random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT'])
                dx, dy = dirs[e['dir']]
                nx, ny = e['x'] + dx, e['y'] + dy
                # Ahora valida bordes Y muros usando tanks_celda_libre
                if self.tanks_celda_libre(nx, ny, 3, 3):
                    e['x'], e['y'] = nx, ny
                else:
                    e['dir'] = random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT'])

                # Probabilidad de disparo enemigo
                if random.random() < 0.15:
                    self.bullets.append({
                        'x': e['x'] + 1,
                        'y': e['y'] + 1,
                        'dir': e['dir'],
                        'owner': 'ENEMY'
                    })

        # 5. TRANSICIÓN AL FINAL BOSS (1000 PUNTOS)
        if self.puntuacion >= 1000 and not self.boss_active:
            self.boss_active = True
            self.enemies = []  # CLEAR_ENEMIES
            # Destruir todos los muros del mapa para abrir la arena del Jefe Final
            for y in range(self.alto):
                for x in range(self.ancho):
                    self.grid[y][x] = 0
            self.boss_x = (self.ancho - 5) // 2
            self.boss_y = 2

        # 6. MOVIMIENTO Y ATAQUE DEL FINAL BOSS (estilo Galaga)
        if self.boss_active and self.boss_hp > 0:
            if self.tanks_tick % 6 == 0:
                self.boss_x += self.boss_dir
                if self.boss_x <= 0 or self.boss_x >= self.ancho - 5:
                    self.boss_dir *= -1
            if self.tanks_tick % 25 == 0:
                # El jefe dispara hacia abajo desde su cañón central
                self.bullets.append({
                    'x': self.boss_x + 2,
                    'y': self.boss_y + 3,
                    'dir': 'DOWN',
                    'owner': 'ENEMY'
                })
        
    def dibujar(self):
        self.canvas.delete("all") # Borrar todo en cada frame
        texto_score = "PUNTUACION\n" + str(self.puntuacion)
        if self.tipo_juego == 'TANKS':
            texto_score += "\n\nVIDAS (HP): " + str(self.player_hp)
            if getattr(self, 'boss_active', False):
                texto_score += "\nBOSS HP: " + str(self.boss_hp)
        self.label_score.config(text=texto_score)
        if self.tipo_juego == 'SNAKE' and self.label_nivel is not None:
            texto = "NIVEL\n" + str(self.niveles[self.nivel_idx].get('nombre', ''))
            if self.estado == 'INVULNERABLE':
                texto += "\nNO MORIR: " + str(int(self.t_fin_invul - time.time()) + 1) + "s"
            self.label_nivel.config(text=texto)
        
        # Colores
        COLOR_GRID_FIJA = '#343434' # Gris oscuro para las celdas fijadas (Tetris)
        COLOR_PIEZA = '#00FFFF'     # Cyan para la pieza activa (Tetris)
        COLOR_SNAKE_CABEZA = '#00FF00' # Verde brillante
        COLOR_SNAKE_CUERPO = '#33CC33' # Verde normal
        COLOR_FOOD = '#FF0000'      # Rojo
        
        # 1. Dibujar la cuadricula estatica (grid base)
        for y in range(self.alto):
            for x in range(self.ancho):
                celda_fija = self.grid[y][x]
                if celda_fija:
                    # Si la celda guarda un color (string) se usa; si no, gris
                    color_fijo = celda_fija if isinstance(celda_fija, basestring) else COLOR_GRID_FIJA
                    self.dibujar_celda(x, y, color_fijo)

        # 2. Dibujar la pieza actual de Tetris
        if self.tipo_juego == 'TETRIS' and self.pieza_actual:
            matriz_pieza = self.pieza_actual[self.pieza_rotacion]
            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        self.dibujar_celda(self.pieza_x + x_offset, self.pieza_y + y_offset, self.pieza_color)
        
        # 3. Dibujar Snake, comida, obstaculos y power-up
        if self.tipo_juego == 'SNAKE':
            # Entidades de la Actividad 4 (listas vacias en el Snake original)
            for (x, y) in self.nubes:
                self.dibujar_nube(x, y)
            for (x, y) in self.venenos:
                self.dibujar_forma(x, y, self.COLOR_VENENO, 'CIRCULAR')
            if self.estrella:
                x, y = self.estrella
                self.dibujar_forma(x, y, self.COLOR_ESTRELLA, 'CIRCULAR')
            # Comida
            if self.posicion_comida:
                x, y = self.posicion_comida
                self.dibujar_celda(x, y, COLOR_FOOD)
            # Cuerpo de la Serpiente
            color_cuerpo = self.color_serpiente or COLOR_SNAKE_CUERPO
            parpadeo = (self.estado == 'INVULNERABLE' and int(time.time() * 6) % 2 == 0)
            for i, segmento in enumerate(self.serpiente_cuerpo):
                x, y = segmento
                if i == 0:
                    # CABEZA
                    color = '#FFFFFF' if parpadeo else COLOR_SNAKE_CABEZA
                    if self.modo_nyan:
                        self.dibujar_cabeza_gato(x, y, '#FFFFFF' if parpadeo else '#AAAAAA')
                    else:
                        self.dibujar_forma(x, y, color, self.forma_serpiente)
                else:
                    # COLA: en Nyan Cat cada segmento toma un color distinto.
                    # i % len(ARCOIRIS) da 0,1,2,3,4,5,0,1,... (se repite)
                    if self.modo_nyan:
                        color = self.ARCOIRIS[i % len(self.ARCOIRIS)]
                    else:
                        color = color_cuerpo
                    self.dibujar_forma(x, y, color, self.forma_serpiente)
                    # 4. Dibujar Brick Tanks (Jugador, Enemigos, Balas, Power-ups y Boss)
        if self.tipo_juego == 'TANKS':
            # Mapeo de dirección a índice de rotación (STATE 1=UP, 2=RIGHT, 3=DOWN, 4=LEFT)
            mapa_rot = {'UP': 0, 'RIGHT': 1, 'DOWN': 2, 'LEFT': 3}
            shapes = self.datos_juego.get('shapes', {})
            attrs = self.datos_juego.get('shape_attrs', {})

            # A. Dibujar Tanque Jugador (brilla en cyan si tiene escudo activo)
            if self.player_hp > 0 and 'PLAYER_TANK' in shapes:
                estados_j = shapes['PLAYER_TANK']
                idx_j = mapa_rot.get(self.player_direction, 0) % len(estados_j)
                escudo_activo = time.time() < getattr(self, 'shield_until', 0)
                color_j = '#00FFFF' if escudo_activo else attrs.get('PLAYER_TANK', {}).get('color', '#00FF00')
                for dy, fila in enumerate(estados_j[idx_j]):
                    for dx, celda in enumerate(fila):
                        if celda == 1:
                            self.dibujar_celda(self.player_x + dx, self.player_y + dy, color_j)

            # B. Dibujar Tanques Enemigos
            for enemigo in self.enemies:
                nombre_e = enemigo['tipo']
                if nombre_e in shapes:
                    estados_e = shapes[nombre_e]
                    idx_e = mapa_rot.get(enemigo.get('dir', 'DOWN'), 0) % len(estados_e)
                    color_e = attrs.get(nombre_e, {}).get('color', '#FF0000')
                    for dy, fila in enumerate(estados_e[idx_e]):
                        for dx, celda in enumerate(fila):
                            if celda == 1:
                                self.dibujar_celda(enemigo['x'] + dx, enemigo['y'] + dy, color_e)

            # C. Dibujar Final Boss (escala gigante 2x2 por cada bloque de su matriz)
            if self.boss_active and self.boss_hp > 0 and 'FINAL_BOSS' in shapes:
                matriz_boss = shapes['FINAL_BOSS'][0]
                color_b = attrs.get('FINAL_BOSS', {}).get('color', '#800080')
                for dy, fila in enumerate(matriz_boss):
                    for dx, celda in enumerate(fila):
                        if celda == 1:
                            for sub_y in range(2):
                                for sub_x in range(2):
                                    self.dibujar_celda(self.boss_x + dx * 2 + sub_x, self.boss_y + dy * 2 + sub_y, color_b)

            # D. Dibujar Power-ups en el mapa (1 celda cada uno con ícono vectorial)
            for pu in self.powerups_activos:
                nombre_pu = pu['tipo'].upper()
                if 'MARTILLO' in nombre_pu or 'REPAIR' in nombre_pu:
                    self.dibujar_martillo(pu['x'], pu['y'])
                else:
                    self.dibujar_escudo(pu['x'], pu['y'])
            # E. Dibujar Balas
            color_bala = attrs.get('BULLET', {}).get('color', '#FFFF00')
            for bala in self.bullets:
                self.dibujar_celda(bala['x'], bala['y'], color_bala)            

    def dibujar_celda(self, x, y, color):
        ts = self.taman_celda # Alias para taman de celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#000000')

    def dibujar_forma(self, x, y, color, forma='RECTANGULAR'):
        # Dibuja UNA celda con la forma pedida en el .brick (FORM:)
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        if forma == 'CIRCULAR':
            self.canvas.create_oval(x1 + 2, y1 + 2, x2 - 2, y2 - 2, fill=color, outline='')
        elif forma == 'TRIANGULAR':
            # create_polygon recibe los vertices: punta arriba, base abajo
            self.canvas.create_polygon(x1 + ts // 2, y1 + 2, x2 - 2, y2 - 2, x1 + 2, y2 - 2,
                                       fill=color, outline='')
        else:
            self.dibujar_celda(x, y, color)      # RECTANGULAR (el original)

    def dibujar_cabeza_gato(self, x, y, color):
        # Cabeza del nivel Nyan Cat: circulo + dos orejas triangulares + ojos
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        self.canvas.create_polygon(x1 + 1, y1 + 9, x1 + 3, y1, x1 + 11, y1 + 5, fill=color, outline='#000000')
        self.canvas.create_polygon(x1 + ts - 1, y1 + 9, x1 + ts - 3, y1, x1 + ts - 11, y1 + 5, fill=color, outline='#000000')
        self.canvas.create_oval(x1 + 1, y1 + 3, x1 + ts - 1, y1 + ts - 1, fill=color, outline='#000000')
        self.canvas.create_oval(x1 + 6, y1 + 11, x1 + 10, y1 + 15, fill='#000000')
        self.canvas.create_oval(x1 + ts - 10, y1 + 11, x1 + ts - 6, y1 + 15, fill='#000000')

    def dibujar_nube(self, x, y):
        # Nube obstaculo: dos ovalos superpuestos
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        self.canvas.create_oval(x1 + 1, y1 + 8, x1 + ts - 1, y1 + ts - 2, fill='#DDDDDD', outline='')
        self.canvas.create_oval(x1 + 5, y1 + 2, x1 + ts - 8, y1 + 14, fill='#FFFFFF', outline='')


    def ejecutar_evento(self, nombre_evento):
        if nombre_evento in self.datos_juego['events']:
            for accion in self.datos_juego['events'][nombre_evento]:
                verbo, objeto = accion.get('accion'), accion.get('objeto')
                
                if verbo == 'INCREASE_SCORE': self.puntuacion += int(objeto)
                if verbo == 'GAME_OVER': self.juego_terminado = True

                if self.tipo_juego == 'TETRIS':
                    if verbo == 'SPAWN': self.tetris_spawn_pieza()
                    if verbo == 'MOVE': self.tetris_mover_pieza(accion['params'][0])
                    if verbo == 'ROTATE': self.tetris_rotar_pieza()
                
                if self.tipo_juego == 'SNAKE':
                    if verbo == 'SPAWN' and objeto == 'PLAYER': self.snake_spawn_jugador(accion)
                    if verbo == 'SPAWN' and objeto == 'FOOD': self.snake_spawn_comida()
                    if verbo == 'MOVE' and objeto == 'PLAYER': self.snake_mover_jugador()
                    if verbo == 'GROW': self.snake_crecer()


    # METODOS DE LOGICA DE JUEGO (MANTENIDOS DEL ARCHIVO ORIGINAL)
    # ---------------------------------------------------------------------

    def tetris_elegir_forma_ponderada(self):
        # Seleccion ponderada con la libreria estandar (sin numpy):
        # se acumulan los pesos (CHANCE) y se busca donde cae un numero al azar.
        formas = self.datos_juego['shapes']
        atributos = self.datos_juego.get('shape_attrs', {})
        nombres = sorted(formas.keys())
        pesos = [max(0, int(atributos.get(n, {}).get('chance', 1))) for n in nombres]
        total = sum(pesos)
        if total <= 0:
            return random.choice(nombres)
        r = random.random() * total
        acumulado = 0
        for nombre, peso in zip(nombres, pesos):
            acumulado += peso
            if r < acumulado:
                return nombre
        return nombres[-1]

    def powerup_estado(self, nombre):
        if nombre not in self.pu_estado:
            self.pu_estado[nombre] = {'lineas_ok': False, 'rot': 0}
        return self.pu_estado[nombre]

    def powerup_listo(self, nombre, pu):
        # Un power-up aparece cuando se cumplen TODAS las condiciones que define
        tl = pu.get('trigger_lineas', 0)
        tr = pu.get('trigger_rotacion')
        if not tl and not tr:
            return False
        est = self.powerup_estado(nombre)
        if tl and not est['lineas_ok']:
            return False
        if tr and est['rot'] < tr['veces']:
            return False
        return True

    def powerup_registrar_lineas(self, cantidad):
        # Condicion: limpiar n lineas SIMULTANEAMENTE
        for nombre, pu in self.datos_juego.get('powerups', {}).items():
            tl = pu.get('trigger_lineas', 0)
            if tl and cantidad >= tl:
                self.powerup_estado(nombre)['lineas_ok'] = True

    def powerup_registrar_rotacion(self):
        # Condicion: rotar n veces una pieza determinada (ej. la L)
        if self.pieza_es_powerup or not self.pieza_nombre:
            return
        for nombre, pu in self.datos_juego.get('powerups', {}).items():
            tr = pu.get('trigger_rotacion')
            if tr and tr['shape'] == self.pieza_nombre:
                self.powerup_estado(nombre)['rot'] += 1

    def powerup_aplicar_efecto(self, pu, celdas):
        self.puntuacion += int(pu.get('puntos', 0))
        efecto = pu.get('efecto')
        if efecto == 'CLEAR_ROW':
            # Borra la(s) fila(s) donde cayo el power-up
            for gy in sorted(set([c[1] for c in celdas])):
                del self.grid[gy]
                self.grid.insert(0, [0] * self.ancho)
        elif efecto == 'FILL_COLUMN':
            # Se incrusta rellenando los huecos de su columna hacia abajo
            for gx, gy in celdas:
                for yy in range(gy, self.alto):
                    if self.grid[yy][gx] == 0:
                        self.grid[yy][gx] = pu.get('color', '#FFFFFF')

    def tetris_spawn_pieza(self):
        powerups = self.datos_juego.get('powerups', {})
        pu_elegido = None
        for nombre in sorted(powerups.keys()):
            if self.powerup_listo(nombre, powerups[nombre]):
                pu_elegido = nombre
                break
        if pu_elegido:
            pu = powerups[pu_elegido]
            self.pieza_actual = pu['estados']
            self.pieza_color = pu.get('color', '#FFD700')
            self.pieza_nombre = pu_elegido
            self.pieza_es_powerup = True
            self.powerup_actual = pu
            self.pu_estado[pu_elegido] = {'lineas_ok': False, 'rot': 0}
        else:
            nombre_pieza = self.tetris_elegir_forma_ponderada()
            atributos = self.datos_juego.get('shape_attrs', {}).get(nombre_pieza, {})
            self.pieza_actual = self.datos_juego['shapes'][nombre_pieza]
            self.pieza_color = atributos.get('color', '#00FFFF')
            self.pieza_nombre = nombre_pieza
            self.pieza_es_powerup = False
            self.powerup_actual = None
        self.pieza_x, self.pieza_y, self.pieza_rotacion = self.ancho / 2 - 2, 0, 0
        if self.tetris_verificar_colision(self.pieza_x, self.pieza_y, self.pieza_rotacion):
            self.juego_terminado = True

    def tetris_mover_pieza(self, direccion):
        if not self.pieza_actual: return
        dx, dy = 0, 0
        if direccion == 'LEFT': dx = -1
        elif direccion == 'RIGHT': dx = 1
        elif direccion == 'DOWN': dy = 1
        if not self.tetris_verificar_colision(self.pieza_x + dx, self.pieza_y + dy, self.pieza_rotacion):
            self.pieza_x += dx
            self.pieza_y += dy
        elif dy > 0:
            self.tetris_fijar_pieza()

    def tetris_rotar_pieza(self):
        if not self.pieza_actual: return
        nueva_rotacion = (self.pieza_rotacion + 1) % len(self.pieza_actual)
        if not self.tetris_verificar_colision(self.pieza_x, self.pieza_y, nueva_rotacion):
            self.pieza_rotacion = nueva_rotacion
            self.powerup_registrar_rotacion()

    def tetris_fijar_pieza(self):
        matriz_pieza = self.pieza_actual[self.pieza_rotacion]
        celdas = []
        for y_offset, fila in enumerate(matriz_pieza):
            for x_offset, celda in enumerate(fila):
                if celda == 1:
                    if 0 <= self.pieza_y + y_offset < self.alto and 0 <= self.pieza_x + x_offset < self.ancho:
                        # Se guarda el color de la pieza en la celda fija
                        self.grid[self.pieza_y + y_offset][self.pieza_x + x_offset] = self.pieza_color
                        celdas.append((self.pieza_x + x_offset, self.pieza_y + y_offset))
        era_powerup, pu = self.pieza_es_powerup, self.powerup_actual
        self.pieza_actual = None
        self.pieza_es_powerup = False
        self.powerup_actual = None
        if era_powerup and pu:
            self.powerup_aplicar_efecto(pu, celdas)
        self.tetris_limpiar_lineas()
        self.ejecutar_evento('ON_START')

    def tetris_verificar_colision(self, x, y, rotacion):
        if not self.pieza_actual: return False
        matriz_pieza = self.pieza_actual[rotacion]
        for y_offset, fila in enumerate(matriz_pieza):
            for x_offset, celda in enumerate(fila):
                if celda == 1:
                    nuevo_x, nuevo_y = x + x_offset, y + y_offset
                    if not (0 <= nuevo_x < self.ancho and 0 <= nuevo_y < self.alto and self.grid[nuevo_y][nuevo_x] == 0):
                        return True
        return False

    def tetris_limpiar_lineas(self):
        nuevo_grid = [fila for fila in self.grid if not all(fila)]
        lineas_limpias = self.alto - len(nuevo_grid)
        if lineas_limpias > 0:
            self.grid = [[0] * self.ancho for _ in range(lineas_limpias)] + nuevo_grid
            self.powerup_registrar_lineas(lineas_limpias)
            for _ in range(lineas_limpias): self.ejecutar_evento('ON_LINE_CLEAR')
    
    def snake_spawn_jugador(self, accion):
        coords = accion['params'][0] if accion['params'] else [self.ancho / 2, self.alto / 2]
        self.serpiente_cuerpo = [(coords[0], coords[1])]
        self.serpiente_direccion = (1, 0)
        
    # ------------------------------------------------------------------
    # ACTIVIDAD 4: NIVELES, OBSTACULOS Y POWER-UP "NO MORIR" (SNAKE)
    # ------------------------------------------------------------------
    def aplicar_nivel(self, idx):
        # Carga la configuracion del nivel idx (viene del bloque LEVELS del .brick)
        n = self.niveles[idx]
        self.nivel_idx = idx
        if 'speed' in n:
            # ms -> segundos. Se divide entre 1000.0 (con .0) porque en
            # Python 2.7 la division de enteros (200 / 1000) da 0.
            self.velocidad_gravedad = n['speed'] / 1000.0
        self.penalizacion_veneno = n.get('poison', 0)
        self.duracion_invul = n.get('invulnerable', 0)
        self.modo_nyan = bool(n.get('nyan', 0))
        # Cada nivel empieza con sus propios obstaculos
        self.nubes = []
        self.venenos = []
        self.estrella = None
        for _ in range(n.get('clouds', 0)):
            celda = self.snake_celda_libre(3)       # no cerca de la cabeza
            if celda:
                self.nubes.append(celda)
        if self.penalizacion_veneno:
            celda = self.snake_celda_libre()
            if celda:
                self.venenos.append(celda)
        if self.duracion_invul:
            self.estrella = self.snake_celda_libre()

    def snake_celda_libre(self, distancia_cabeza=0):
        # Devuelve una celda (x, y) vacia al azar, o None si no queda ninguna.
        # distancia_cabeza > 0: tambien evita las celdas cercanas a la cabeza.
        ocupadas = set(self.serpiente_cuerpo) | set(self.nubes) | set(self.venenos)
        if self.posicion_comida:
            ocupadas.add(self.posicion_comida)
        if self.estrella:
            ocupadas.add(self.estrella)
        libres = []
        for x in range(self.ancho):
            for y in range(self.alto):
                if (x, y) in ocupadas:
                    continue
                if distancia_cabeza and self.serpiente_cuerpo:
                    hx, hy = self.serpiente_cuerpo[0]
                    if abs(x - hx) + abs(y - hy) <= distancia_cabeza:
                        continue
                libres.append((x, y))
        if not libres:
            return None
        return random.choice(libres)

    def snake_spawn_comida(self):
        celda = self.snake_celda_libre()
        if celda:
            self.posicion_comida = celda

    def snake_actualizar_estado(self):
        # MANEJADOR DE ESTADOS: se llama en cada frame.
        # NORMAL --(come la estrella)--> INVULNERABLE --(pasan n segundos)--> NORMAL
        ahora = time.time()
        if self.estado == 'INVULNERABLE' and ahora >= self.t_fin_invul:
            self.estado = 'NORMAL'
            self.t_proxima_estrella = ahora + self.INTERVALO_ESTRELLA
        if (self.estado == 'NORMAL' and self.duracion_invul and self.estrella is None
                and ahora >= self.t_proxima_estrella):
            self.estrella = self.snake_celda_libre()

    def snake_revisar_nivel(self):
        # Sube de nivel cuando el puntaje alcanza NEXT_AT del nivel actual
        n = self.niveles[self.nivel_idx]
        if 'next_at' in n and self.nivel_idx + 1 < len(self.niveles) \
                and self.puntuacion >= n['next_at']:
            self.aplicar_nivel(self.nivel_idx + 1)

    def snake_mover_jugador(self):
        if not self.serpiente_cuerpo: return
        cabeza_x, cabeza_y = self.serpiente_cuerpo[0]
        dir_x, dir_y = self.serpiente_direccion
        nueva_cabeza = (cabeza_x + dir_x, cabeza_y + dir_y)
        invulnerable = (self.estado == 'INVULNERABLE')

        # 1. PARED: normal -> evento ON_COLLISION_WALL (game over en el .brick).
        #    Invulnerable -> reaparece por el lado opuesto (% = modulo).
        if not (0 <= nueva_cabeza[0] < self.ancho and 0 <= nueva_cabeza[1] < self.alto):
            if invulnerable:
                nueva_cabeza = (nueva_cabeza[0] % self.ancho, nueva_cabeza[1] % self.alto)
            else:
                self.ejecutar_evento('ON_COLLISION_WALL')
                return

        # 2. CUERPO PROPIO (invulnerable lo atraviesa)
        if nueva_cabeza in self.serpiente_cuerpo[:-1] and not invulnerable:
            self.ejecutar_evento('ON_COLLISION_SELF')
            return

        # 3. NUBE: pierde TODOS los puntos pero sigue vivo; si ya tenia 0 -> game over
        if nueva_cabeza in self.nubes and not invulnerable:
            if self.puntuacion > 0:
                self.puntuacion = 0
            else:
                self.juego_terminado = True
                return

        self.serpiente_cuerpo.insert(0, nueva_cabeza)

        # 4. QUE SE COMIO
        if nueva_cabeza == self.posicion_comida:
            self.ejecutar_evento('ON_EAT_FOOD')         # crece (no se hace pop)
        elif nueva_cabeza in self.venenos:
            self.puntuacion = max(0, self.puntuacion - self.penalizacion_veneno)
            self.venenos.remove(nueva_cabeza)
            celda = self.snake_celda_libre()
            if celda:
                self.venenos.append(celda)
            self.serpiente_cuerpo.pop()                 # no crece
        elif nueva_cabeza == self.estrella:
            self.estado = 'INVULNERABLE'
            self.t_fin_invul = time.time() + self.duracion_invul
            self.estrella = None
            self.serpiente_cuerpo.pop()
        else:
            self.serpiente_cuerpo.pop()

        self.snake_revisar_nivel()

    def snake_cambiar_direccion(self, direccion):
        if direccion == 'UP' and self.serpiente_direccion[1] != 1:
            self.serpiente_direccion = (0, -1)
        elif direccion == 'DOWN' and self.serpiente_direccion[1] != -1:
            self.serpiente_direccion = (0, 1)
        elif direccion == 'LEFT' and self.serpiente_direccion[0] != 1:
            self.serpiente_direccion = (-1, 0)
        elif direccion == 'RIGHT' and self.serpiente_direccion[0] != -1:
            self.serpiente_direccion = (1, 0)

    def snake_crecer(self):
        pass


    # METODOS DE SALIDA (ADAPTADOS A GUI)
    # -----------------------------------

    def mostrar_game_over(self):
        # Muestra una ventana de mensaje de Tkinter
        tkMessageBox.showinfo("Juego Terminado", "Puntuacion Final: " + str(self.puntuacion))
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print ("Uso: python runtime.py <archivo_juego.json>")
        sys.exit(1)
    archivo_juego = sys.argv[1]
    try:
        with open(archivo_juego, 'r') as f:
            datos_juego = json.load(f)
    except IOError:
        print ("Error: No se pudo encontrar el archivo ") + archivo_juego
        sys.exit(1)
    juego = Juego(datos_juego)
    juego.run()
    
