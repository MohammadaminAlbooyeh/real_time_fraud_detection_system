from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

class WordleGame(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        self.add_widget(Label(text='Welcome to Wordle!'))

        self.input = TextInput(hint_text='Enter your guess', multiline=False)
        self.add_widget(self.input)

        self.submit_button = Button(text='Submit Guess')
        self.submit_button.bind(on_press=self.submit_guess)
        self.add_widget(self.submit_button)

        self.result_label = Label(text='')
        self.add_widget(self.result_label)

    def submit_guess(self, instance):
        guess = self.input.text
        # Placeholder for game logic
        self.result_label.text = f'You guessed: {guess}'

class WordleApp(App):
    def build(self):
        return WordleGame()

if __name__ == '__main__':
    WordleApp().run()