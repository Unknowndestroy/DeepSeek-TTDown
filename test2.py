import socket
import threading
import time
import sys
import select
import os
import random

# Windows ve Unix için farklı key input
try:
    import msvcrt
except ImportError:
    import tty
    import termios

class PongGame:
    def __init__(self):
        self.board_width = 80
        self.board_height = 20
        self.paddle_height = 4
        self.ball_pos = [self.board_width // 2, self.board_height // 2]
        self.ball_vel = [1, -1]
        self.left_paddle = self.board_height // 2 - self.paddle_height // 2
        self.right_paddle = self.board_height // 2 - self.paddle_height // 2
        self.left_score = 0
        self.right_score = 0
        self.game_active = False
        self.paused = False
        self.difficulty = "NORMAL"
        self.ball_speed = 1.0
        self.multiplayer = False
        self.is_server = False
        self.connection = None
        self.control_scheme = "ARROWS"
        self.miss_count = 0
        self.max_misses = 3
        self.server_ip = "127.0.0.1"
        self.port = 5555
        self.connected = False
        self.waiting_for_connection = False

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def draw_board(self):
        self.clear_screen()
        
        # Skor (sağ üst köşe)
        score_line = " " * (self.board_width - 20) + f"SKOR: {self.left_score} - {self.right_score}"
        print(score_line)
        
        # Üst sınır
        print("+" + "-" * self.board_width + "+")
        
        # Oyun alanı
        for y in range(self.board_height):
            line = "|"
            for x in range(self.board_width):
                if (x == 0 and self.left_paddle <= y < self.left_paddle + self.paddle_height):
                    line += "|"
                elif (x == self.board_width - 1 and self.right_paddle <= y < self.right_paddle + self.paddle_height):
                    line += "|"
                elif (x == self.ball_pos[0] and y == self.ball_pos[1]):
                    line += "O"
                else:
                    line += " "
            line += "|"
            print(line)
        
        # Alt sınır
        print("+" + "-" * self.board_width + "+")
        
        # Bilgiler
        info_line = f"Zorluk: {self.difficulty} | Kaçırma: {self.miss_count}/{self.max_misses}"
        if self.multiplayer:
            role = "Server" if self.is_server else "Client"
            info_line += f" | {role}"
            if self.waiting_for_connection:
                info_line += " | Bağlantı bekleniyor..."
            elif self.connected:
                info_line += " | BAĞLANDI"
        
        print(info_line)
        print("Kontroller: ↑↓ veya WS - Çıkış: ESC")

    def setup_terminal(self):
        if os.name != 'nt':
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())

    def restore_terminal(self):
        if os.name != 'nt':
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_input(self):
        try:
            if os.name == 'nt':
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b'\xe0':  # Ok tuşları
                        key = msvcrt.getch()
                        if key == b'H': return 'UP'
                        if key == b'P': return 'DOWN'
                        if key == b'K': return 'LEFT'
                        if key == b'M': return 'RIGHT'
                    elif key == b'\x1b': return 'ESC'
                    elif key == b' ': return 'SPACE'
                    elif key == b'w' or key == b'W': return 'W'
                    elif key == b's' or key == b'S': return 'S'
                return None
            else:
                # Unix sistemler
                dr, dw, de = select.select([sys.stdin], [], [], 0)
                if dr:
                    key = sys.stdin.read(1)
                    if key == '\x1b':  # Escape sequence
                        key = sys.stdin.read(2)  # Ok tuşları [A, [B, [C, [D
                        if key == '[A': return 'UP'
                        if key == '[B': return 'DOWN'
                        if key == '[C': return 'RIGHT'
                        if key == '[D': return 'LEFT'
                    elif key == ' ': return 'SPACE'
                    elif key == 'w' or key == 'W': return 'W'
                    elif key == 's' or key == 'S': return 'S'
                return None
        except:
            return None

    def show_menu(self, title, options):
        self.clear_screen()
        print(f"=== {title} ===")
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        return input("Seçiminiz (1-" + str(len(options)) + "): ")

    def main_menu(self):
        while True:
            # Zorluk seçimi
            diff_choice = self.show_menu("ZORLUK SEÇİMİ", 
                ["KOLAY", "NORMAL", "ZOR"])
            
            if diff_choice == "1": 
                self.difficulty = "KOLAY"
                self.ball_speed = 0.8
                break
            elif diff_choice == "2": 
                self.difficulty = "NORMAL" 
                self.ball_speed = 1.0
                break
            elif diff_choice == "3": 
                self.difficulty = "ZOR"
                self.ball_speed = 1.3
                break

        # Multiplayer seçimi
        mp_choice = self.show_menu("MULTIPLAYER", 
            ["TEK OYUNCU", "MULTIPLAYER"])
        self.multiplayer = (mp_choice == "2")

        # Kontrol seçimi
        control_choice = self.show_menu("KONTROL SEÇİMİ",
            ["OK TUŞLARI (↑↓)", "WASD (WS)", "FARE (Sadece PC)" if os.name == 'nt' else "FARE (Mevcut değil)"])
        
        if control_choice == "1": self.control_scheme = "ARROWS"
        elif control_choice == "2": self.control_scheme = "WASD"
        elif control_choice == "3" and os.name == 'nt': self.control_scheme = "MOUSE"
        else: self.control_scheme = "ARROWS"

        if self.multiplayer:
            role_choice = self.show_menu("BAĞLANTI TİPİ", 
                ["SERVER (Bağlantı Bekler)", "CLIENT (Bağlanır)"])
            self.is_server = (role_choice == "1")
            
            if not self.is_server:
                self.server_ip = input("Server IP adresi (localhost için boş bırakın): ")
                if not self.server_ip:
                    self.server_ip = "127.0.0.1"

        self.start_game()

    def start_server(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(1)
            server_socket.settimeout(0.5)
            
            self.waiting_for_connection = True
            start_time = time.time()
            
            while self.waiting_for_connection and time.time() - start_time < 30:  # 30 saniye timeout
                self.draw_board()
                print(f"\nBağlantı bekleniyor... Port: {self.port}")
                print("İptal etmek için ESC'ye basın")
                
                try:
                    self.connection, addr = server_socket.accept()
                    self.connected = True
                    self.waiting_for_connection = False
                    print(f"\nBağlantı kabul edildi: {addr}")
                    break
                except socket.timeout:
                    pass
                
                key = self.get_input()
                if key == 'ESC':
                    self.waiting_for_connection = False
                    break
                
                time.sleep(0.1)
            
            server_socket.close()
            
        except Exception as e:
            print(f"Server hatası: {e}")
            input("Devam etmek için Enter'a basın...")

    def connect_to_server(self):
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(5)
            self.connection.connect((self.server_ip, self.port))
            self.connected = True
            print("Server'a bağlanıldı!")
        except Exception as e:
            print(f"Bağlantı hatası: {e}")
            input("Devam etmek için Enter'a basın...")
            self.connected = False

    def countdown(self):
        for i in range(3, 0, -1):
            self.draw_board()
            print(f"\n>>> {i} <<<")
            time.sleep(1)
        self.draw_board()
        print("\n>>> BAŞLA! <<<")
        time.sleep(0.5)

    def start_game(self):
        self.setup_terminal()
        
        try:
            if self.multiplayer:
                if self.is_server:
                    self.start_server()
                else:
                    self.connect_to_server()
                
                if self.connected:
                    self.countdown()
                else:
                    self.multiplayer = False
                    print("Multiplayer başarısız, tek oyuncu moduna geçiliyor...")
                    time.sleep(2)

            self.game_loop()
        finally:
            self.restore_terminal()

    def update_game(self):
        if not self.game_active or self.paused:
            return

        # Topu hareket ettir
        self.ball_pos[0] += int(self.ball_vel[0] * self.ball_speed)
        self.ball_pos[1] += int(self.ball_vel[1] * self.ball_speed)

        # Üst ve alt duvarlardan sekme
        if self.ball_pos[1] <= 0 or self.ball_pos[1] >= self.board_height - 1:
            self.ball_vel[1] *= -1

        # Sol paddle kontrolü
        if self.ball_pos[0] <= 1:
            if (self.left_paddle <= self.ball_pos[1] < self.left_paddle + self.paddle_height):
                self.ball_vel[0] = abs(self.ball_vel[0])  # Sağa dön
                # Topun paddle'ın neresine çarptığına göre açı değiştir
                paddle_center = self.left_paddle + self.paddle_height // 2
                offset = (self.ball_pos[1] - paddle_center) / (self.paddle_height // 2)
                self.ball_vel[1] = offset
            else:
                self.right_score += 1
                self.miss_count += 1
                self.reset_ball()

        # Sağ paddle kontrolü
        elif self.ball_pos[0] >= self.board_width - 2:
            if (self.right_paddle <= self.ball_pos[1] < self.right_paddle + self.paddle_height):
                self.ball_vel[0] = -abs(self.ball_vel[0])  # Sola dön
                # Topun paddle'ın neresine çarptığına göre açı değiştir
                paddle_center = self.right_paddle + self.paddle_height // 2
                offset = (self.ball_pos[1] - paddle_center) / (self.paddle_height // 2)
                self.ball_vel[1] = offset
            else:
                self.left_score += 1
                self.miss_count += 1
                self.reset_ball()

        # 3 kaçırmada oyunu bitir
        if self.miss_count >= self.max_misses:
            self.game_over()
            return

        # Tek oyuncu modunda bilgisayarın paddle hareketi
        if not self.multiplayer:
            self.ai_move()

    def reset_ball(self):
        self.ball_pos = [self.board_width // 2, self.board_height // 2]
        # Rastgele başlangıç yönü
        self.ball_vel = [random.choice([-1, 1]), random.choice([-1, 1])]
        time.sleep(0.5)  # Kısa bekleme

    def game_over(self):
        self.draw_board()
        loser = "SOL" if self.miss_count >= self.max_misses else "SAĞ"
        print(f"\n>>> OYUN BİTTİ! {loser} TARAF KAYBETTİ <<<")
        print("3 kez kaçırıldı!")
        input("Devam etmek için Enter'a basın...")
        
        # Skorları sıfırla
        self.left_score = 0
        self.right_score = 0
        self.miss_count = 0
        self.reset_ball()

    def ai_move(self):
        # Basit AI: topun y pozisyonunu takip et
        target_y = self.ball_pos[1] - self.paddle_height // 2
        
        # Zorluk seviyesine göre AI hassasiyeti
        if self.difficulty == "KOLAY":
            if random.random() < 0.3:  # %30 hata yapma şansı
                target_y += random.randint(-2, 2)
        elif self.difficulty == "ZOR":
            # Daha iyi takip
            pass
            
        target_y = max(0, min(self.board_height - self.paddle_height, target_y))
        
        # Yumuşak hareket
        if self.right_paddle < target_y:
            self.right_paddle += 1
        elif self.right_paddle > target_y:
            self.right_paddle -= 1

    def handle_input(self, key):
        if key == 'ESC':
            self.pause_menu()
            return
        
        if key == 'SPACE' and not self.game_active:
            self.game_active = True
            return

        # Sol paddle kontrolü (Player 1 veya Server)
        if (self.multiplayer and self.is_server) or not self.multiplayer:
            if self.control_scheme == "ARROWS":
                if key == 'UP' and self.left_paddle > 0:
                    self.left_paddle -= 1
                elif key == 'DOWN' and self.left_paddle < self.board_height - self.paddle_height:
                    self.left_paddle += 1
            elif self.control_scheme == "WASD":
                if key == 'W' and self.left_paddle > 0:
                    self.left_paddle -= 1
                elif key == 'S' and self.left_paddle < self.board_height - self.paddle_height:
                    self.left_paddle += 1

        # Sağ paddle kontrolü (Player 2 veya Client)
        if (self.multiplayer and not self.is_server) or not self.multiplayer:
            if self.control_scheme == "ARROWS":
                if key == 'UP' and self.right_paddle > 0:
                    self.right_paddle -= 1
                elif key == 'DOWN' and self.right_paddle < self.board_height - self.paddle_height:
                    self.right_paddle += 1
            elif self.control_scheme == "WASD":
                if key == 'W' and self.right_paddle > 0:
                    self.right_paddle -= 1
                elif key == 'S' and self.right_paddle < self.board_height - self.paddle_height:
                    self.right_paddle += 1

    def network_send_receive(self):
        if not self.connection or not self.connected:
            return

        try:
            if self.is_server:
                # Server: client'tan veri al, kendi verisini gönder
                self.connection.setblocking(False)
                try:
                    data = self.connection.recv(1024).decode()
                    if data:
                        self.right_paddle = int(data)
                except:
                    pass
                
                # Server durumu gönder
                data_to_send = f"{self.ball_pos[0]},{self.ball_pos[1]},{self.left_paddle},{self.left_score},{self.right_score},{self.miss_count}"
                self.connection.send(data_to_send.encode())
            else:
                # Client: server'a veri gönder, server durumunu al
                self.connection.send(str(self.right_paddle).encode())
                
                self.connection.setblocking(False)
                try:
                    data = self.connection.recv(1024).decode()
                    if data:
                        parts = data.split(',')
                        if len(parts) == 6:
                            self.ball_pos[0] = int(parts[0])
                            self.ball_pos[1] = int(parts[1])
                            self.left_paddle = int(parts[2])
                            self.left_score = int(parts[3])
                            self.right_score = int(parts[4])
                            self.miss_count = int(parts[5])
                except:
                    pass
        except:
            self.connected = False

    def pause_menu(self):
        self.paused = True
        self.restore_terminal()
        
        while self.paused:
            choice = self.show_menu("PAUSE MENÜSÜ", 
                ["Devam Et", "Zorluk Değiştir", "Kontrolleri Değiştir", 
                 "Multiplayer Ayarları", "Ana Menü", "Çıkış"])
            
            if choice == "1":
                self.paused = False
            elif choice == "2":
                self.change_difficulty()
            elif choice == "3":
                self.change_controls()
            elif choice == "4":
                self.change_multiplayer()
            elif choice == "5":
                self.paused = False
                self.game_active = False
                self.main_menu()
                return
            elif choice == "6":
                self.paused = False
                self.game_active = False
                sys.exit(0)
        
        self.setup_terminal()

    def change_difficulty(self):
        diff_choice = self.show_menu("ZORLUK SEÇİMİ", 
            ["KOLAY", "NORMAL", "ZOR"])
        
        if diff_choice == "1": 
            self.difficulty = "KOLAY"
            self.ball_speed = 0.8
        elif diff_choice == "2": 
            self.difficulty = "NORMAL"
            self.ball_speed = 1.0
        elif diff_choice == "3": 
            self.difficulty = "ZOR"
            self.ball_speed = 1.3

    def change_controls(self):
        control_choice = self.show_menu("KONTROL SEÇİMİ",
            ["OK TUŞLARI (↑↓)", "WASD (WS)", "FARE (Sadece PC)" if os.name == 'nt' else "FARE (Mevcut değil)"])
        
        if control_choice == "1": 
            self.control_scheme = "ARROWS"
        elif control_choice == "2": 
            self.control_scheme = "WASD"
        elif control_choice == "3" and os.name == 'nt': 
            self.control_scheme = "MOUSE"

    def change_multiplayer(self):
        mp_choice = self.show_menu("MULTIPLAYER", 
            ["TEK OYUNCU", "MULTIPLAYER"])
        
        new_mp = (mp_choice == "2")
        
        if new_mp != self.multiplayer:
            self.multiplayer = new_mp
            if self.multiplayer:
                role_choice = self.show_menu("BAĞLANTI TİPİ", 
                    ["SERVER (Bağlantı Bekler)", "CLIENT (Bağlanır)"])
                self.is_server = (role_choice == "1")
                
                if not self.is_server:
                    self.server_ip = input("Server IP adresi: ")
                    if not self.server_ip:
                        self.server_ip = "127.0.0.1"
            
            # Bağlantıyı kapat
            if self.connection:
                self.connection.close()
                self.connection = None
                self.connected = False

    def game_loop(self):
        self.game_active = True
        
        while self.game_active:
            if not self.paused:
                self.update_game()
                self.draw_board()
                
                if self.multiplayer and self.connected:
                    self.network_send_receive()

            # Girdi işleme
            key = self.get_input()
            if key:
                self.handle_input(key)

            time.sleep(0.05)  # 20 FPS

def main():
    try:
        game = PongGame()
        game.main_menu()
    except KeyboardInterrupt:
        print("\nOyundan çıkılıyor...")
    except Exception as e:
        print(f"Bir hata oluştu: {e}")
        input("Devam etmek için Enter'a basın...")

if __name__ == "__main__":
    main()