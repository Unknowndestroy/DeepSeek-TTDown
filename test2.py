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

class VerticalPongGame:
    def __init__(self):
        # Dikey oyun için boyutlar (Termux için optimize)
        self.board_width = 25
        self.board_height = 40
        self.paddle_width = 3
        self.ball_pos = [self.board_width // 2, self.board_height // 2]
        self.ball_vel = [1, -1]
        self.top_paddle = self.board_width // 2 - self.paddle_width // 2
        self.bottom_paddle = self.board_width // 2 - self.paddle_width // 2
        self.top_score = 0
        self.bottom_score = 0
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
        
        # ASCII sanat - PONG başlığı
        print("╔═════════════════════════╗")
        print("║         P O N G         ║")
        print("╚═════════════════════════╝")
        
        # Skor gösterimi
        print(f"   TOP: {self.top_score}     BOTTOM: {self.bottom_score}")
        print(" " + "═" * 27)
        
        # Oyun alanı - DİKEY
        for y in range(self.board_height):
            line = "║"
            for x in range(self.board_width):
                # Üst paddle (y == 1 satırında)
                if y == 1 and self.top_paddle <= x < self.top_paddle + self.paddle_width:
                    line += "█"
                # Alt paddle (y == board_height-2 satırında)
                elif y == self.board_height - 2 and self.bottom_paddle <= x < self.bottom_paddle + self.paddle_width:
                    line += "█"
                # Top
                elif x == self.ball_pos[0] and y == self.ball_pos[1]:
                    line += "●"
                # Sol ve sağ duvarlar
                elif x == 0 or x == self.board_width - 1:
                    line += "│"
                # Boş alan
                else:
                    line += " "
            line += "║"
            print(line)
        
        # Alt bilgi çubuğu
        print(" " + "═" * 27)
        info_line = f"Zorluk: {self.difficulty} | Kaçırma: {self.miss_count}/{self.max_misses}"
        if self.multiplayer:
            role = "Server" if self.is_server else "Client"
            status = "BAĞLANDI" if self.connected else "BEKLENİYOR"
            info_line += f" | {role} ({status})"
        print(info_line)
        
        # Kontroller
        if self.control_scheme == "ARROWS":
            print("Kontroller: ← → (Sol/Sağ)")
        else:
            print("Kontroller: A D (Sol/Sağ)")
        print("Başlat: SPACE | Duraklat: ESC")

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
                        if key == b'K': return 'LEFT'
                        if key == b'M': return 'RIGHT'
                    elif key == b'\x1b': return 'ESC'
                    elif key == b' ': return 'SPACE'
                    elif key == b'a' or key == b'A': return 'A'
                    elif key == b'd' or key == b'D': return 'D'
                return None
            else:
                # Unix sistemler (Termux)
                dr, dw, de = select.select([sys.stdin], [], [], 0)
                if dr:
                    key = sys.stdin.read(1)
                    if key == '\x1b':  # Escape sequence
                        key = sys.stdin.read(2)  # Ok tuşları
                        if key == '[D': return 'LEFT'
                        if key == '[C': return 'RIGHT'
                    elif key == ' ': return 'SPACE'
                    elif key == 'a' or key == 'A': return 'A'
                    elif key == 'd' or key == 'D': return 'D'
                    elif key == '\n': return 'ENTER'
                return None
        except:
            return None

    def show_menu(self, title, options):
        self.clear_screen()
        print("╔═════════════════════════╗")
        print(f"║       {title:^15}       ║")
        print("╠═════════════════════════╣")
        for i, option in enumerate(options, 1):
            print(f"║  {i}. {option:<19} ║")
        print("╚═════════════════════════╝")
        return input("Seçiminiz (1-" + str(len(options)) + "): ")

    def main_menu(self):
        while True:
            # Zorluk seçimi
            diff_choice = self.show_menu("ZORLUK", 
                ["KOLAY", "NORMAL", "ZOR"])
            
            if diff_choice == "1": 
                self.difficulty = "KOLAY"
                self.ball_speed = 0.7
                break
            elif diff_choice == "2": 
                self.difficulty = "NORMAL" 
                self.ball_speed = 1.0
                break
            elif diff_choice == "3": 
                self.difficulty = "ZOR"
                self.ball_speed = 1.4
                break
            else:
                print("Geçersiz seçim! Tekrar deneyin.")
                time.sleep(1)

        # Multiplayer seçimi
        while True:
            mp_choice = self.show_menu("MOD", 
                ["TEK OYUNCU", "MULTIPLAYER"])
            if mp_choice in ["1", "2"]:
                self.multiplayer = (mp_choice == "2")
                break
            else:
                print("Geçersiz seçim! Tekrar deneyin.")
                time.sleep(1)

        # Kontrol seçimi
        while True:
            control_choice = self.show_menu("KONTROLLER",
                ["OK TUŞLARI", "A/D TUŞLARI"])
            
            if control_choice == "1": 
                self.control_scheme = "ARROWS"
                break
            elif control_choice == "2": 
                self.control_scheme = "WASD"
                break
            else:
                print("Geçersiz seçim! Tekrar deneyin.")
                time.sleep(1)

        if self.multiplayer:
            while True:
                role_choice = self.show_menu("ROL", 
                    ["SERVER", "CLIENT"])
                if role_choice in ["1", "2"]:
                    self.is_server = (role_choice == "1")
                    break
                else:
                    print("Geçersiz seçim! Tekrar deneyin.")
                    time.sleep(1)
            
            if not self.is_server:
                ip = input("Server IP (boş=bırak localhost): ")
                self.server_ip = ip if ip else "127.0.0.1"

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
            
            while self.waiting_for_connection and time.time() - start_time < 30:
                self.draw_board()
                print(f"\n⏳ Bağlantı bekleniyor... Port: {self.port}")
                print("İptal için ESC'ye basın")
                
                try:
                    self.connection, addr = server_socket.accept()
                    self.connected = True
                    self.waiting_for_connection = False
                    print(f"✅ Bağlantı kuruldu: {addr[0]}")
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
            print(f"❌ Server hatası: {e}")
            input("Devam etmek için Enter'a basın...")

    def connect_to_server(self):
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(5)
            print(f"🔗 {self.server_ip}:{self.port} bağlanılıyor...")
            self.connection.connect((self.server_ip, self.port))
            self.connected = True
            print("✅ Server'a bağlanıldı!")
        except Exception as e:
            print(f"❌ Bağlantı hatası: {e}")
            input("Devam etmek için Enter'a basın...")
            self.connected = False

    def countdown(self):
        for i in range(3, 0, -1):
            self.draw_board()
            print(f"\n🎯 {i} 🎯")
            time.sleep(1)
        self.draw_board()
        print("\n🚀 BAŞLA!")
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
                    print("❌ Multiplayer başarısız, tek oyuncu moduna geçiliyor...")
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

        # Sol ve sağ duvarlardan sekme
        if self.ball_pos[0] <= 1 or self.ball_pos[0] >= self.board_width - 2:
            self.ball_vel[0] *= -1

        # Üst paddle kontrolü
        if self.ball_pos[1] <= 2:
            if (self.top_paddle <= self.ball_pos[0] < self.top_paddle + self.paddle_width):
                self.ball_vel[1] = abs(self.ball_vel[1])  # Aşağı dön
                # Topun paddle'ın neresine çarptığına göre açı değiştir
                paddle_center = self.top_paddle + self.paddle_width // 2
                offset = (self.ball_pos[0] - paddle_center) / (self.paddle_width // 2)
                self.ball_vel[0] = offset * 2
            else:
                self.bottom_score += 1
                self.miss_count += 1
                self.reset_ball()

        # Alt paddle kontrolü
        elif self.ball_pos[1] >= self.board_height - 3:
            if (self.bottom_paddle <= self.ball_pos[0] < self.bottom_paddle + self.paddle_width):
                self.ball_vel[1] = -abs(self.ball_vel[1])  # Yukarı dön
                # Topun paddle'ın neresine çarptığına göre açı değiştir
                paddle_center = self.bottom_paddle + self.paddle_width // 2
                offset = (self.ball_pos[0] - paddle_center) / (self.paddle_width // 2)
                self.ball_vel[0] = offset * 2
            else:
                self.top_score += 1
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
        self.ball_vel = [random.choice([-1, 1]) * 0.5, random.choice([-1, 1])]
        time.sleep(0.5)

    def game_over(self):
        self.draw_board()
        loser = "ÜST" if self.miss_count >= self.max_misses else "ALT"
        print(f"\n💀 OYUN BİTTİ! {loser} TARAF KAYBETTİ 💀")
        print(f"📊 Son skor: {self.top_score} - {self.bottom_score}")
        print("⏳ Yeni oyun başlatılıyor...")
        time.sleep(3)
        
        # Skorları sıfırla
        self.top_score = 0
        self.bottom_score = 0
        self.miss_count = 0
        self.reset_ball()

    def ai_move(self):
        # Basit AI: topun x pozisyonunu takip et
        target_x = self.ball_pos[0] - self.paddle_width // 2
        
        # Zorluk seviyesine göre AI hassasiyeti
        if self.difficulty == "KOLAY":
            if random.random() < 0.4:  # %40 hata yapma şansı
                target_x += random.randint(-3, 3)
        elif self.difficulty == "ZOR":
            # Daha iyi takip + öngörü
            if self.ball_vel[1] > 0:  # Top aşağı iniyorsa
                predict_x = self.ball_pos[0] + self.ball_vel[0] * 5
                target_x = predict_x - self.paddle_width // 2
            
        target_x = max(1, min(self.board_width - self.paddle_width - 1, target_x))
        
        # Yumuşak hareket
        if self.top_paddle < target_x:
            self.top_paddle += 1
        elif self.top_paddle > target_x:
            self.top_paddle -= 1

    def handle_input(self, key):
        if key == 'ESC':
            self.pause_menu()
            return
        
        if key == 'SPACE' and not self.game_active:
            self.game_active = True
            return

        # Paddle hareketleri
        paddle_speed = 2
        
        # Üst paddle kontrolü (Server veya tek oyuncu)
        if (self.multiplayer and self.is_server) or not self.multiplayer:
            if key == 'LEFT' or key == 'A':
                if self.top_paddle > 1:
                    self.top_paddle = max(1, self.top_paddle - paddle_speed)
            elif key == 'RIGHT' or key == 'D':
                if self.top_paddle < self.board_width - self.paddle_width - 1:
                    self.top_paddle = min(self.board_width - self.paddle_width - 1, self.top_paddle + paddle_speed)

        # Alt paddle kontrolü (Client veya tek oyuncu)
        if (self.multiplayer and not self.is_server) or not self.multiplayer:
            if key == 'LEFT' or key == 'A':
                if self.bottom_paddle > 1:
                    self.bottom_paddle = max(1, self.bottom_paddle - paddle_speed)
            elif key == 'RIGHT' or key == 'D':
                if self.bottom_paddle < self.board_width - self.paddle_width - 1:
                    self.bottom_paddle = min(self.board_width - self.paddle_width - 1, self.bottom_paddle + paddle_speed)

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
                        self.bottom_paddle = int(data)
                except:
                    pass
                
                # Server durumu gönder
                data_to_send = f"{self.ball_pos[0]},{self.ball_pos[1]},{self.top_paddle},{self.top_score},{self.bottom_score},{self.miss_count}"
                self.connection.send(data_to_send.encode())
            else:
                # Client: server'a veri gönder, server durumunu al
                self.connection.send(str(self.bottom_paddle).encode())
                
                self.connection.setblocking(False)
                try:
                    data = self.connection.recv(1024).decode()
                    if data:
                        parts = data.split(',')
                        if len(parts) == 6:
                            self.ball_pos[0] = int(parts[0])
                            self.ball_pos[1] = int(parts[1])
                            self.top_paddle = int(parts[2])
                            self.top_score = int(parts[3])
                            self.bottom_score = int(parts[4])
                            self.miss_count = int(parts[5])
                except:
                    pass
        except:
            self.connected = False

    def pause_menu(self):
        self.paused = True
        self.restore_terminal()
        
        while self.paused:
            choice = self.show_menu("DURAKLATILDI", 
                ["▶ Devam Et", "🎯 Zorluk", "🎮 Kontroller", 
                 "🌐 Multiplayer", "🏠 Ana Menü", "❌ Çıkış"])
            
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
                return
            elif choice == "6":
                self.paused = False
                self.game_active = False
                sys.exit(0)
        
        self.setup_terminal()

    def change_difficulty(self):
        diff_choice = self.show_menu("ZORLUK", 
            ["KOLAY", "NORMAL", "ZOR"])
        
        if diff_choice == "1": 
            self.difficulty = "KOLAY"
            self.ball_speed = 0.7
        elif diff_choice == "2": 
            self.difficulty = "NORMAL"
            self.ball_speed = 1.0
        elif diff_choice == "3": 
            self.difficulty = "ZOR"
            self.ball_speed = 1.4

    def change_controls(self):
        control_choice = self.show_menu("KONTROLLER",
            ["OK TUŞLARI", "A/D TUŞLARI"])
        
        if control_choice == "1": 
            self.control_scheme = "ARROWS"
        elif control_choice == "2": 
            self.control_scheme = "WASD"

    def change_multiplayer(self):
        mp_choice = self.show_menu("MOD", 
            ["TEK OYUNCU", "MULTIPLAYER"])
        
        new_mp = (mp_choice == "2")
        
        if new_mp != self.multiplayer:
            self.multiplayer = new_mp
            if self.multiplayer:
                role_choice = self.show_menu("ROL", 
                    ["SERVER", "CLIENT"])
                self.is_server = (role_choice == "1")
                
                if not self.is_server:
                    ip = input("Server IP: ")
                    self.server_ip = ip if ip else "127.0.0.1"
            
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

            time.sleep(0.08)  # Daha yavaş FPS - Termux için optimize

def main():
    try:
        game = VerticalPongGame()
        while True:
            game.main_menu()
    except KeyboardInterrupt:
        print("\n👋 Oyundan çıkılıyor...")
    except Exception as e:
        print(f"❌ Bir hata oluştu: {e}")
        input("Devam etmek için Enter'a basın...")

if __name__ == "__main__":
    main()