import tkinter as tk
from tkinter import messagebox, simpledialog
from main import generate_random_names
import random

class WordleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Wordle Multiplayer Game")
        self.setup_start_screen()

    def setup_start_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="Select Difficulty:").pack()
        self.diff_var = tk.StringVar(value="2")
        tk.Radiobutton(self.root, text="Easy (4 letters, 5 attempts)", variable=self.diff_var, value="1").pack(anchor="w")
        tk.Radiobutton(self.root, text="Medium (5 letters, 3 attempts)", variable=self.diff_var, value="2").pack(anchor="w")
        tk.Radiobutton(self.root, text="Hard (6 letters, 2 attempts)", variable=self.diff_var, value="3").pack(anchor="w")
        tk.Label(self.root, text="Number of Players:").pack()
        self.players_entry = tk.Entry(self.root)
        self.players_entry.pack()
        tk.Button(self.root, text="Start Game", command=self.start_game).pack(pady=10)

    def start_game(self):
        try:
            num_players = int(self.players_entry.get())
            if num_players < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Enter a valid number of players.")
            return
        diff = self.diff_var.get()
        if diff == "1":
            self.word_length = 4
            self.attempts = 5
        elif diff == "2":
            self.word_length = 5
            self.attempts = 3
        else:
            self.word_length = 6
            self.attempts = 2
        self.num_players = num_players
        self.all_names = generate_random_names(num_names=1000, name_length=self.word_length)
        self.computer_names = random.sample(self.all_names, 5)
        self.current_player = 1
        self.results = []
        self.player_names = []
        self.setup_player_names_screen()

    def setup_player_names_screen(self):
        self.clear_screen()
        tk.Label(self.root, text=f"Player {self.current_player}: Enter 6 names ({self.word_length} letters each)").pack()
        self.name_entries = [tk.Entry(self.root) for _ in range(6)]
        for entry in self.name_entries:
            entry.pack()
        tk.Button(self.root, text="Submit Names", command=self.submit_player_names).pack(pady=10)

    def submit_player_names(self):
        names = [entry.get() for entry in self.name_entries]
        if any(len(name) != self.word_length for name in names):
            messagebox.showerror("Error", f"All names must be exactly {self.word_length} letters.")
            return
        self.player_names.append(names)
        self.guesses = []
        self.attempt_num = 1
        self.setup_guess_screen()

    def setup_guess_screen(self):
        self.clear_screen()
        tk.Label(self.root, text=f"Player {self.current_player}: Attempt {self.attempt_num} of {self.attempts}").pack()
        self.guess_entry = tk.Entry(self.root)
        self.guess_entry.pack()
        tk.Button(self.root, text="Submit Guess", command=self.submit_guess).pack(pady=10)

    def submit_guess(self):
        guess = self.guess_entry.get()
        if len(guess) != self.word_length:
            messagebox.showerror("Error", f"Guess must be exactly {self.word_length} letters.")
            return
        self.guesses.append(guess)
        if guess in self.computer_names:
            self.results.append((self.current_player, True))
            self.next_player()
        else:
            if self.attempt_num < self.attempts:
                self.attempt_num += 1
                messagebox.showinfo("Wrong Guess", "Wrong guess. Try again.")
                self.setup_guess_screen()
            else:
                self.results.append((self.current_player, False))
                self.next_player()

    def next_player(self):
        if self.current_player < self.num_players:
            self.current_player += 1
            self.setup_player_names_screen()
        else:
            self.show_results()

    def show_results(self):
        self.clear_screen()
        tk.Label(self.root, text="Game Results:").pack()
        for player, win in self.results:
            tk.Label(self.root, text=f"Player {player}: {'win' if win else 'lose'}").pack()
        tk.Button(self.root, text="Play Again", command=self.setup_start_screen).pack(pady=10)

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WordleGUI(root)
    root.mainloop()
