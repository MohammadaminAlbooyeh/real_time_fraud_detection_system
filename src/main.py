from random import randint, seed
import csv
import os
import string

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
    import random
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
    results = []
    for player in range(1, num_players + 1):
        print(f"\nPlayer {player}, enter your 6 names:")
        user_names = get_user_names(num_names=6, name_length=word_length)
        print(f"Player {player}, try to guess one of the computer's selected names!")
        win = False
        for attempt in range(1, attempts + 1):
            guess = input(f"Attempt {attempt}: Enter your guess (exactly {word_length} characters): ")
            if guess in computer_names:
                win = True
                break
            else:
                print("Wrong guess.")
        results.append((player, win))
    # Step 6: Print results
    print("\nGame Results:")
    for player, win in results:
        print(f"Player {player}: {'win' if win else 'lose'}")

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