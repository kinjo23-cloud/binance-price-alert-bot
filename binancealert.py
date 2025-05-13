import tkinter as tk
from tkinter import messagebox
import threading
import json
import websocket
import time
import winsound

# Binance USD-M Futures WebSocket endpoint
def get_ws_url(symbol):
    return f"wss://fstream.binance.com/ws/{symbol.lower()}@trade"

class PriceAlertBot:
    def continuous_beep(self, duration_seconds=600, beep_interval=0.1):
        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            if self.stop_beep:
                break
            try:
                winsound.Beep(1000, 500)  # 500ms beep
            except Exception as e:
                print("Sound error:", e)
                break
            time.sleep(beep_interval)  # Short pause between beeps

    def __init__(self, master):
        self.master = master
        self.ws = None
        self.running = False
        self.alerts = []
        self.reconnect_delay = 5
        self.stop_beep = False

        master.title("Binance Futures Price Alert Bot")
        master.geometry("500x500")

        # Symbol input
        tk.Label(master, text="Symbol (e.g., BTCUSDT)").pack()
        self.symbol_entry = tk.Entry(master)
        self.symbol_entry.pack()

        # Target price input
        tk.Label(master, text="Target Price").pack()
        self.price_entry = tk.Entry(master)
        self.price_entry.pack()

        # Direction
        self.direction = tk.StringVar(value="cross_up")
        tk.Radiobutton(master, text="Cross Up", variable=self.direction, value="cross_up").pack()
        tk.Radiobutton(master, text="Cross Down", variable=self.direction, value="cross_down").pack()

        # Add Alert button
        self.add_button = tk.Button(master, text="Add Alert", command=self.add_alert)
        self.add_button.pack(pady=5)

        # Alerts list
        self.alerts_listbox = tk.Listbox(master)
        self.alerts_listbox.pack(pady=10, fill=tk.BOTH, expand=True)

        # Start and Stop buttons
        self.start_button = tk.Button(master, text="Start Monitoring", command=self.start)
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(master, text="Stop Monitoring", command=self.stop, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        # Stop Program button
        self.stop_program_button = tk.Button(master, text="Stop Program", command=self.stop_program)
        self.stop_program_button.pack(pady=5)

        # Status label
        self.status_label = tk.Label(master, text="Status: Idle")
        self.status_label.pack(pady=10)

    def stop_program(self):
        # Stop the bot and close the application
        self.running = False
        if self.ws:
            self.ws.close()
        self.master.quit()  # This will terminate the Tkinter application

    def add_alert(self):
        symbol = self.symbol_entry.get().strip().upper()
        try:
            target_price = float(self.price_entry.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "Target price must be a number.")
            return
        direction = self.direction.get()

        if not symbol:
            messagebox.showerror("Input Error", "Symbol is required.")
            return

        if len(self.alerts) >= 10:
            messagebox.showwarning("Limit Reached", "Maximum of 10 alerts allowed.")
            return

        alert = {"symbol": symbol, "price": target_price, "direction": direction}
        self.alerts.append(alert)
        self.alerts_listbox.insert(tk.END, f"{symbol} {direction.replace('_', ' ').upper()} {target_price}")

    def on_message(self, ws, message):
        data = json.loads(message)
        price = float(data['p'])
        symbol = data['s'].upper()

        for alert in self.alerts:
            if alert['symbol'] != symbol:
                continue

            if alert['direction'] == "cross_up" and price >= alert['price']:
                self.alert(f"{symbol} price crossed UP {alert['price']}! Current price: {price}")
            elif alert['direction'] == "cross_down" and price <= alert['price']:
                self.alert(f"{symbol} price crossed DOWN {alert['price']}! Current price: {price}")

    def on_error(self, ws, error):
        print("WebSocket error:", error)
        if self.running:
            self.start_beeping_during_connection_loss()

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed")
        if self.running:
            self.start_beeping_during_connection_loss()

    def on_open(self, ws):
        print("WebSocket connection opened")

    def start_beeping_during_connection_loss(self):
        self.stop_beep = False
        threading.Thread(target=self.continuous_beep, daemon=True).start()

    def start(self):
        if not self.alerts:
            messagebox.showwarning("No Alerts", "Please add at least one alert before starting.")
            return

        symbol = self.alerts[0]['symbol'].lower()  # WebSocket allows one symbol per connection
        self.running = True
        self.status_label.config(text="Status: Monitoring...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        def run_ws():
            ws_url = get_ws_url(symbol)
            self.ws = websocket.WebSocketApp(ws_url,
                                             on_message=self.on_message,
                                             on_error=self.on_error,
                                             on_close=self.on_close,
                                             on_open=self.on_open)
            while self.running:
                self.ws.run_forever()
                time.sleep(self.reconnect_delay)  # Wait before attempting to reconnect

        self.thread = threading.Thread(target=run_ws)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        self.stop_beep = True  # Stop beeping when the monitoring stops
        self.status_label.config(text="Status: Stopped")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def alert(self, msg):
        print(msg)
        self.stop_beep = False
        try:
            self.stop_beep = False  # Reset stop flag
            threading.Thread(target=self.continuous_beep, daemon=True).start()
        except Exception as e:
            print("Sound error:", e)
        messagebox.showinfo("Price Alert", msg)
        self.stop_beep = True  # Stop the beeping once the user clicks OK

    def refresh_alerts_listbox(self):
        self.alerts_listbox.delete(0, tk.END)
        for alert in self.alerts:
            self.alerts_listbox.insert(tk.END, f"{alert['symbol']} {alert['direction'].replace('_', ' ').upper()} {alert['price']}")

if __name__ == '__main__':
    root = tk.Tk()
    app = PriceAlertBot(root)
    root.mainloop()
