import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime
import sqlite3
import threading
import time
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import csv
 
 
class ReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SOP & License Tracker - Kamran Saifullah")
        self.root.geometry("1200x600")
 
        self.conn = sqlite3.connect("tracker.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup_db()
 
        self.tray_icon = None
        self.selected_sop_id = None
        self.selected_license_id = None
 
        self.setup_ui()
        self.load_data()
        threading.Thread(target=self.check_reminders, daemon=True).start()
 
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
 
    def setup_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                initial_date TEXT,
                next_date TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                initial_date TEXT,
                next_date TEXT
            )
        """)
        self.conn.commit()
 
    def setup_ui(self):
        input_frame = tk.Frame(self.root)
        input_frame.pack(padx=10, pady=10)
 
        sop_frame = tk.LabelFrame(input_frame, text="Manage SOPs", padx=10, pady=10)
        sop_frame.grid(row=0, column=0, padx=10)
 
        license_frame = tk.LabelFrame(input_frame, text="Manage Licenses", padx=10, pady=10)
        license_frame.grid(row=0, column=1, padx=10)
 
        # SOP
        tk.Label(sop_frame, text="SOP Name:").grid(row=0, column=0)
        self.sop_name = tk.Entry(sop_frame)
        self.sop_name.grid(row=0, column=1)
 
        tk.Label(sop_frame, text="Initial Approval Date:").grid(row=1, column=0)
        self.sop_initial = DateEntry(sop_frame, date_pattern="yyyy-MM-dd")
        self.sop_initial.grid(row=1, column=1)
 
        tk.Label(sop_frame, text="Next Approval Date:").grid(row=2, column=0)
        self.sop_next = DateEntry(sop_frame, date_pattern="yyyy-MM-dd")
        self.sop_next.grid(row=2, column=1)
 
        tk.Button(sop_frame, text="Add SOP", command=self.add_sop).grid(row=3, column=0, pady=5)
        tk.Button(sop_frame, text="Update SOP", command=self.update_sop).grid(row=3, column=1)
        tk.Button(sop_frame, text="Delete SOP", command=self.delete_sop).grid(row=4, column=0, columnspan=2)
 
        # License
        tk.Label(license_frame, text="License Name:").grid(row=0, column=0)
        self.license_name = tk.Entry(license_frame)
        self.license_name.grid(row=0, column=1)
 
        tk.Label(license_frame, text="Initial Approval Date:").grid(row=1, column=0)
        self.license_initial = DateEntry(license_frame, date_pattern="yyyy-MM-dd")
        self.license_initial.grid(row=1, column=1)
 
        tk.Label(license_frame, text="Next Renewal Date:").grid(row=2, column=0)
        self.license_next = DateEntry(license_frame, date_pattern="yyyy-MM-dd")
        self.license_next.grid(row=2, column=1)
 
        tk.Button(license_frame, text="Add License", command=self.add_license).grid(row=3, column=0, pady=5)
        tk.Button(license_frame, text="Update License", command=self.update_license).grid(row=3, column=1)
        tk.Button(license_frame, text="Delete License", command=self.delete_license).grid(row=4, column=0, columnspan=2)
 
        tk.Button(self.root, text="Export to CSV", command=self.export_csv).pack(pady=5)
 
        display_frame = tk.Frame(self.root)
        display_frame.pack(fill="both", expand=True)
 
        self.sop_table = self.create_table(display_frame, "SOPs")
        self.license_table = self.create_table(display_frame, "Licenses")
 
    def create_table(self, parent, label):
        frame = tk.Frame(parent)
        frame.pack(side="left", padx=10, fill="both", expand=True)
 
        table = ttk.Treeview(frame, columns=("ID", "Name", "Initial Date", "Next Date", "Days Left"),
                             show="headings")
        for col in table["columns"]:
            table.heading(col, text=col)
            table.column(col, anchor="center", width=150)
 
        table.pack(fill="both", expand=True)
 
        if label == "SOPs":
            table.bind("<Double-1>", self.select_sop)
        else:
            table.bind("<Double-1>", self.select_license)
 
        table.tag_configure("red", background="#ffcccc")
        table.tag_configure("yellow", background="#fff3cd")
 
        return table
 
    def calculate_days_left(self, next_date_str):
        try:
            today = datetime.today()
            next_dt = datetime.strptime(next_date_str, "%Y-%m-%d")
            return (next_dt - today).days
        except:
            return None
 
    def load_data(self):
        self.load_table("sops", self.sop_table)
        self.load_table("licenses", self.license_table)
 
    def load_table(self, db_table, table):
        for row in table.get_children():
            table.delete(row)
        self.cursor.execute(f"SELECT id, name, initial_date, next_date FROM {db_table}")
        for rec in self.cursor.fetchall():
            days_left = self.calculate_days_left(rec[3])
            tag = ""
            if days_left is not None:
                if 0 <= days_left <= 15:
                    tag = "red"
                elif 16 <= days_left <= 30:
                    tag = "yellow"
            table.insert('', 'end', values=(*rec, days_left), tags=(tag,))
 
    def add_sop(self):
        self.add_entry("sops", self.sop_name.get(), self.sop_initial.get(), self.sop_next.get())
        self.clear_fields()
 
    def update_sop(self):
        self.update_entry("sops", self.selected_sop_id, self.sop_name.get(), self.sop_initial.get(), self.sop_next.get())
        self.clear_fields()
 
    def delete_sop(self):
        self.delete_entry("sops", self.sop_table, self.selected_sop_id)
        self.clear_fields()
 
    def select_sop(self, event):
        item = self.sop_table.selection()[0]
        values = self.sop_table.item(item)["values"]
        self.selected_sop_id = values[0]
        self.sop_name.delete(0, tk.END)
        self.sop_name.insert(0, values[1])
        self.sop_initial.set_date(values[2])
        self.sop_next.set_date(values[3])
 
    def add_license(self):
        self.add_entry("licenses", self.license_name.get(), self.license_initial.get(), self.license_next.get())
        self.clear_fields()
 
    def update_license(self):
        self.update_entry("licenses", self.selected_license_id, self.license_name.get(),
                          self.license_initial.get(), self.license_next.get())
        self.clear_fields()
 
    def delete_license(self):
        self.delete_entry("licenses", self.license_table, self.selected_license_id)
        self.clear_fields()
 
    def select_license(self, event):
        item = self.license_table.selection()[0]
        values = self.license_table.item(item)["values"]
        self.selected_license_id = values[0]
        self.license_name.delete(0, tk.END)
        self.license_name.insert(0, values[1])
        self.license_initial.set_date(values[2])
        self.license_next.set_date(values[3])
 
    def add_entry(self, table, name, initial_date, next_date):
        if not name:
            messagebox.showerror("Error", "Name is required.")
            return
        self.cursor.execute(f"INSERT INTO {table} (name, initial_date, next_date) VALUES (?, ?, ?)",
                            (name, initial_date, next_date))
        self.conn.commit()
        self.load_data()
 
    def update_entry(self, table, rec_id, name, initial_date, next_date):
        if not name or not rec_id:
            return
        self.cursor.execute(f"UPDATE {table} SET name=?, initial_date=?, next_date=? WHERE id=?",
                            (name, initial_date, next_date, rec_id))
        self.conn.commit()
        self.load_data()
 
    def delete_entry(self, table, treeview, rec_id):
        if not rec_id:
            return
        self.cursor.execute(f"DELETE FROM {table} WHERE id=?", (rec_id,))
        self.conn.commit()
        self.load_data()
        treeview.selection_remove(treeview.selection())
 
    def clear_fields(self):
        self.sop_name.delete(0, tk.END)
        self.license_name.delete(0, tk.END)
        self.selected_sop_id = None
        self.selected_license_id = None
 
    def check_reminders(self):
        shown = set()
        while True:
            for db_table, label in [("sops", "SOP"), ("licenses", "License")]:
                self.cursor.execute(f"SELECT name, next_date FROM {db_table}")
                for name, next_date in self.cursor.fetchall():
                    try:
                        days_left = self.calculate_days_left(next_date)
                        key = f"{label}:{name}"
                        if 0 <= days_left <= 30 and key not in shown:
                            self.show_popup(f"{label} '{name}' is due in {days_left} day(s)!")
                            shown.add(key)
                        if days_left < 0 and key in shown:
                            shown.remove(key)
                    except:
                        continue
            time.sleep(60)
 
    def show_popup(self, msg):
        def popup():
            messagebox.showinfo("Reminder", msg)
        self.root.after(0, popup)
 
    def hide_window(self):
        self.root.withdraw()
        if not self.tray_icon:
            self.create_tray_icon()
 
    def create_image(self):
        image = Image.new('RGB', (64, 64), "blue")
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill="white")
        return image
 
    def create_tray_icon(self):
        image = self.create_image()
        menu = (item('Show', self.show_window), item('Exit', self.exit_app))
        self.tray_icon = pystray.Icon("Tracker", image, "SOP & License Tracker", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
 
    def show_window(self):
        self.root.deiconify()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
 
    def exit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.conn.close()
        self.root.destroy()
 
    def export_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv")
        if not file_path:
            return
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Type", "ID", "Name", "Initial Date", "Next Date", "Days Left"])
            for tname, label in [("sops", "SOP"), ("licenses", "License")]:
                self.cursor.execute(f"SELECT id, name, initial_date, next_date FROM {tname}")
                for row in self.cursor.fetchall():
                    days = self.calculate_days_left(row[3])
                    writer.writerow([label, *row, days])
        messagebox.showinfo("Exported", f"Data exported to {file_path}")
 
 
if __name__ == "__main__":
    root = tk.Tk()
    app = ReminderApp(root)
    root.mainloop()