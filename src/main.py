from random import randint, seed
import csv
import os
import string
import random
from speech_recognition import Recognizer, Microphone

seed(42)  # For reproducibility

def generate_word(length=5):
    """Generate a random word of given length."""
    return ''.join([string.ascii_lowercase[randint(0, 25)] for _ in range(length)])

def generate_word_frequencies(num_words=1000, max_frequency=100):
    """Generate a dictionary of words with random frequencies."""
    word_frequencies = {}
    for i in range(num_words):
        word = generate_word()
        frequency = randint(1, max_frequency)
        word_frequencies[word] = frequency
    return word_frequencies

def save_word_frequencies_to_csv(word_frequencies, filename="word_frequencies.csv"):
    """Save the word frequencies dictionary to a CSV file in the current working directory."""
    filepath = os.path.join(os.getcwd(), filename)
    with open(filepath, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["word", "frequency"])
        for word, freq in word_frequencies.items():
            writer.writerow([word, freq])

def generate_random_words_with_frequencies(num_words=1000, word_length=5, max_frequency=100):
    """Generate a dictionary of random words with random frequencies."""
    word_frequencies = {}
    for _ in range(num_words):
        word = generate_word(word_length)
        frequency = randint(1, max_frequency)
        word_frequencies[word] = frequency
    return word_frequencies

def generate_random_names(num_names=1000, name_length=5):
    """Generate a list of random names with given length."""
    names = set()
    while len(names) < num_names:
        name = generate_word(name_length)
        names.add(name)
    return list(names)

def get_user_names(num_names=6, name_length=5):
    """Prompt the user to enter names num_names times, each with exact name_length characters."""
    names = []
    for i in range(num_names):
        while True:
            name = input(f"Enter name {i+1} (exactly {name_length} characters): ")
            if len(name) == name_length:
                names.append(name)
                break
            else:
                print(f"Name must be exactly {name_length} characters. Please try again.")
    return names

def play_game():
    pass

def play_multiplayer_game():
    # Step 1: Select difficulty
    print("Select difficulty level:")
    print("1. Easy (word length 4, 5 attempts)")
    print("2. Medium (word length 5, 3 attempts)")
    print("3. Hard (word length 6, 2 attempts)")
    while True:
        diff = input("Enter 1, 2, or 3: ")
        if diff == "1":
            word_length = 4
            attempts = 5
            break
        elif diff == "2":
            word_length = 5
            attempts = 3
            break
        elif diff == "3":
            word_length = 6
            attempts = 2
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    # Step 2: Generate 1000 random names
    all_names = generate_random_names(num_names=1000, name_length=word_length)
    # Step 3: Computer selects 5 names from the list
    computer_names = random.sample(all_names, 5)
    print("Computer has selected 5 secret names.")
    # Step 4: Get number of players
    while True:
        try:
            num_players = int(input("Enter number of players: "))
            if num_players > 0:
                break
            else:
                print("Number of players must be positive.")
        except ValueError:
            print("Please enter a valid integer.")
    # Step 5: For each player, get names and play
    # Load dictionary
    try:
        with open("dictionary.txt", "r") as f:
            valid_words = set(line.strip().lower() for line in f if line.strip())
    except FileNotFoundError:
        print("Warning: dictionary.txt not found. All guesses will be accepted.")
        valid_words = None

    results = []
    history = []
    for player in range(1, num_players + 1):
        print(f"\nPlayer {player}, enter your 6 names:")
        user_names = get_user_names(num_names=6, name_length=word_length)
        print(f"Player {player}, try to guess one of the computer's selected names!")
        guesses = []
        win = False
        for attempt in range(1, attempts + 1):
            while True:
                guess = input(f"Attempt {attempt}: Enter your guess (exactly {word_length} characters): ").lower()
                if len(guess) != word_length:
                    print(f"Guess must be exactly {word_length} characters.")
                    continue
                if valid_words is not None and guess not in valid_words:
                    print("Not a valid word. Try again.")
                    continue
                break
            guesses.append(guess)
            if guess in computer_names:
                win = True
                break
            else:
                print("Wrong guess.")
        results.append((player, win))
        history.append({
            "player": player,
            "user_names": user_names,
            "guesses": guesses,
            "result": "win" if win else "lose"
        })
    # Step 6: Print results
    print("\nGame Results:")
    for player, win in results:
        print(f"Player {player}: {'win' if win else 'lose'}")

    # Save game history to CSV
    with open("game_history.csv", mode="a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["player", "user_names", "guesses", "result"])
        for entry in history:
            writer.writerow([
                entry["player"],
                ",".join(entry["user_names"]),
                ",".join(entry["guesses"]),
                entry["result"]
            ])

if __name__ == "__main__":
    play_multiplayer_game()

if __name__ == "__main__":
    play_game()

def save_real_names_to_csv(names_file="names.txt", output_csv="real_names.csv", num_names=1000, name_length=5):
    """Read real names from a file, filter by length, and save to CSV."""
    with open(names_file, "r") as f:
        all_names = [line.strip() for line in f if len(line.strip()) == name_length]
    selected_names = list(dict.fromkeys(all_names))[:num_names]
    filepath = os.path.join(os.getcwd(), output_csv)
    with open(filepath, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["name"])
        for name in selected_names:
            writer.writerow([name])

# Example usage:
# save_real_names_to_csv()

def user_names_guess(num_names=6, name_length=5):
    """Prompt the user to enter names num_names times, each with exact name_length characters."""
    names = []
    for i in range(num_names):
        while True:
            name = input(f"Enter name {i+1} (exactly {name_length} characters): ")
            if len(name) == name_length:
                names.append(name)
                break
            else:
                print(f"Name must be exactly {name_length} characters. Please try again.")
    return names

def save_real_names_to_csv(names_file="names.txt", output_csv="real_names.csv", num_names=1000, name_length=5):
    """Read real names from a file, filter by length, and save to CSV."""
    # Read names from file
    with open(names_file, "r") as f:
        all_names = [line.strip() for line in f if len(line.strip()) == name_length]
    # Get unique names and limit to num_names
    selected_names = list(dict.fromkeys(all_names))[:num_names]
    # Save to CSV
    filepath = os.path.join(os.getcwd(), output_csv)
    with open(filepath, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["name"])
        for name in selected_names:
            writer.writerow([name])

# Example usage:
if __name__ == "__main__":
    save_real_names_to_csv()
if __name__ == "__main__":
    random_word_freqs = generate_random_words_with_frequencies()
    save_word_frequencies_to_csv(random_word_freqs, filename="random_words.csv")
    user_names = user_names_guess()
    print("User names:", user_names)

class AIOpponent:
    def __init__(self, word_list):
        self.word_list = word_list
        self.possible_words = set(word_list)

    def filter_words(self, feedback, guess):
        """Filter possible words based on feedback."""
        new_possible_words = set()
        for word in self.possible_words:
            match = True
            for i, char in enumerate(guess):
                if feedback[i] == 'G' and word[i] != char:
                    match = False
                    break
                elif feedback[i] == 'Y' and (char not in word or word[i] == char):
                    match = False
                    break
                elif feedback[i] == 'B' and char in word:
                    match = False
                    break
            if match:
                new_possible_words.add(word)
        self.possible_words = new_possible_words

    def make_guess(self):
        """Make a guess from the remaining possible words."""
        return next(iter(self.possible_words)) if self.possible_words else None

# Example usage of AI Opponent
if __name__ == "__main__":
    word_list = generate_random_names(num_names=1000, name_length=5)
    ai = AIOpponent(word_list)

    # Simulate a game
    secret_word = random.choice(word_list)
    print(f"Secret word: {secret_word}")

    for attempt in range(6):
        guess = ai.make_guess()
        if not guess:
            print("AI has no more guesses.")
            break
        print(f"AI guesses: {guess}")

        # Simulate feedback
        feedback = []
        for i, char in enumerate(guess):
            if char == secret_word[i]:
                feedback.append('G')  # Green
            elif char in secret_word:
                feedback.append('Y')  # Yellow
            else:
                feedback.append('B')  # Black

        print(f"Feedback: {''.join(feedback)}")
        if ''.join(feedback) == 'G' * len(secret_word):
            print("AI wins!")
            break

        ai.filter_words(feedback, guess)

def enable_colorblind_mode():
    """Enable alternative visual indicators for colorblind players."""
    print("Colorblind mode enabled. Feedback will use symbols instead of colors.")

def get_feedback_with_symbols(guess, secret_word):
    """Provide feedback using symbols for colorblind mode."""
    feedback = []
    for i, char in enumerate(guess):
        if char == secret_word[i]:
            feedback.append('✔')  # Correct position
        elif char in secret_word:
            feedback.append('✱')  # Misplaced
        else:
            feedback.append('✖')  # Incorrect
    return ''.join(feedback)

def voice_input():
    """Capture voice input and convert it to text."""
    recognizer = Recognizer()
    with Microphone() as source:
        print("Listening for your guess...")
        try:
            audio = recognizer.listen(source)
            guess = recognizer.recognize_google(audio)
            print(f"You said: {guess}")
            return guess
        except Exception as e:
            print(f"Error recognizing voice input: {e}")
            return None

# Example usage
if __name__ == "__main__":
    secret_word = "apple"
    enable_colorblind_mode()
    guess = voice_input()
    if guess:
        feedback = get_feedback_with_symbols(guess, secret_word)
        print(f"Feedback: {feedback}")