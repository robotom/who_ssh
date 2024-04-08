#!/usr/bin/python

import tkinter as tk
from tkinter import scrolledtext, simpledialog, ttk, messagebox
import tailer
import threading
import csv
import subprocess
import re

# Function to monitor the auth.log file
def monitor_auth_log():
    for line in tailer.follow(open('/var/log/auth.log')):
        if 'Accepted' in line:  # Checks for successful login
            text_area.configure(state='normal')
            text_area.insert(tk.END, f"{line}\n", 'green')
            text_area.configure(state='disabled')
            # Schedule the popup to run on the main thread
            root.after(0, show_success_popup, line)
        elif 'session closed for user' in line:  # Checks for logout
            text_area.configure(state='normal')
            text_area.insert(tk.END, f"{line}\n", 'red')
            text_area.configure(state='disabled')
        elif 'Failed password' in line:  # Checks for failed login attempt
            text_area.configure(state='normal')
            text_area.insert(tk.END, f"Failed login attempt: {line}\n", 'yellow')
            text_area.configure(state='disabled')
        text_area.see(tk.END)

# Function to display a popup for successful login
def show_success_popup(message):
    messagebox.showinfo("SSH Login Detected!", message)


# Function to check and display active SSH sessions on startup
def display_active_ssh_sessions():
    ssh_sessions_output = subprocess.check_output('who').decode('utf-8')
    ssh_sessions = [line for line in ssh_sessions_output.split('\n') if line.strip() and "pts/" in line]

    if ssh_sessions:
        text_area.configure(state='normal')
        for session in ssh_sessions:
            text_area.insert(tk.END, f"Active session: {session}\n", 'green')
        text_area.configure(state='disabled')
    else:
        text_area.configure(state='normal')
        text_area.insert(tk.END, "No active SSH sessions.\n", 'green')
        text_area.configure(state='disabled')

# Function to export the log to a CSV file
def export_to_csv():
    filename = 'ssh_log.csv'
    with open(filename, 'w', newline='') as csvfile:
        log_writer = csv.writer(csvfile)
        text_content = text_area.get('1.0', tk.END).strip().split('\n')
        for line in text_content:
            log_writer.writerow([line])
    print(f"Exported to {filename}")

# Function to list and forcibly log out an SSH user session
def force_logout():
    # List current SSH sessions
    ssh_sessions_output = subprocess.check_output('who').decode('utf-8')
    ssh_sessions = [line for line in ssh_sessions_output.split('\n') if line.strip()]

    # Creating a selection dialog to choose which session to kill
    session_info = '\n'.join([f"{idx + 1}: {session}" for idx, session in enumerate(ssh_sessions)])
    selection = simpledialog.askstring("Force Logout", f"Enter the number of the session to logout:\n{session_info}")
    
    if selection and selection.isdigit():
        selection_idx = int(selection) - 1
        if 0 <= selection_idx < len(ssh_sessions):
            # Extracting username and pts from the selected session
            session_details = ssh_sessions[selection_idx].split()
            username, pts = session_details[0], session_details[1]

            # Killing the selected session
            result = subprocess.run(['pkill', '-KILL', '-t', pts], capture_output=True, text=True)
            if result.stderr:
                print(f"Error: {result.stderr}")
            else:
                print(f"Session {selection}: {username} on {pts} has been logged out.")
        else:
            print("Invalid selection.")
    else:
        print("Logout cancelled or invalid input.")


# Function to search within the text
def search_logs():
    search_query = simpledialog.askstring("Search Logs", "Enter search string:")
    if search_query:
        start = '1.0'
        while True:
            start = text_area.search(search_query, start, stopindex=tk.END)
            if not start:
                break
            end = f"{start}+{len(search_query)}c"
            text_area.tag_add('search', start, end)
            start = end
        text_area.tag_config('search', background='yellow')

# GUI setup
root = tk.Tk()
root.title("who SSH monitor")

# Default window size here
root.geometry('400x300')

# Creating frames for text area and buttons
text_frame = tk.Frame(root)
text_frame.pack(fill=tk.BOTH, expand=True)

button_frame = tk.Frame(root)
button_frame.pack(fill=tk.X)

text_area = scrolledtext.ScrolledText(text_frame, width=70, height=10)  # Adjusted width and height
text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
text_area.tag_config('green', foreground='green')
text_area.tag_config('red', foreground='red')

# Buttons for additional functionalities, now with adjusted size
export_button = tk.Button(button_frame, text="Export", command=export_to_csv)
export_button.pack(side=tk.LEFT, padx=5, pady=5)

logout_button = tk.Button(button_frame, text="Logout", command=force_logout)
logout_button.pack(side=tk.LEFT, padx=5, pady=5)

search_button = tk.Button(button_frame, text="Search", command=search_logs)
search_button.pack(side=tk.LEFT, padx=5, pady=5)

# Display active SSH sessions on startup
display_active_ssh_sessions()

# Run the monitoring in separate thread
thread = threading.Thread(target=monitor_auth_log)
thread.daemon = True
thread.start()

root.mainloop()
