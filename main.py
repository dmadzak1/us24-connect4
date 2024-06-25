import ili9xxx
from machine import SPI, Pin, ADC
import lvgl as lv
import time
import gc
import random

# Initialize SPI and display driver
spi = SPI(0, baudrate=62500000, miso=Pin(16), mosi=Pin(19), sck=Pin(18))
drv = ili9xxx.Ili9341(spi=spi, dc=15, cs=17, rst=20)

adc_x = ADC(Pin(28))
select = Pin(17)

# Make screen object
scr = lv.obj()

# Create a title label
title = lv.label(scr)
title.set_text("Connect4")
title.align(lv.ALIGN.CENTER, 0, -10)  

# Create the buttons
btnSP = lv.button(scr)
btnMP = lv.button(scr)
btnSP.align(lv.ALIGN.CENTER, -60, 30)
btnMP.align(lv.ALIGN.CENTER, 65, 30)
labelSP = lv.label(btnSP)
labelSP.set_text('SinglePlayer')
labelMP = lv.label(btnMP)
labelMP.set_text('Multiplayer')

# Current selected button index
selected_button_index = 0

# Function to update button selection based on analog stick input
def update_button_selection():
    global selected_button_index,labelSP,labelMP
    
    # Read analog values from the analog stick (adjust these based on your analog stick's behavior)
    x_val = adc_x.read_u16()
    
    # Example logic: determine button selection based on analog stick position
    if x_val < 2000:
        selected_button_index = 0  # Select btnSP
    elif x_val > 60000:
        selected_button_index = 1  # Select btnMP

    # Highlight the selected button
    labelSP.set_text('SinglePlayer')  # Reset btnSP to plain style
    labelMP.set_text('MultiPlayer')  # Reset btnMP to plain style
    if selected_button_index == 0:
        labelSP.set_text('Select SP?')  # Highlight btnSP
    elif selected_button_index == 1:
        labelMP.set_text('Select MP?')  # Highlight btnMP

# Load screen
lv.screen_load(scr)

position = 0

def column_selection():
    global adc_x, select, position
    # Read analog values from the analog stick (adjust these based on your analog stick's behavior)
    
    # Example logic: determine button selection based on analog stick position
    if adc_x.read_u16() < 2000 and position > 0:
          position-=1
          while adc_x.read_u16()<2000:
              pass
    if adc_x.read_u16() > 60000 and position <6:
          position+=1
          while adc_x.read_u16()>60000:
              pass
    return position

def show_winner_screen(winner):
    global scr
    scr_winner = lv.obj()
    label = lv.label(scr_winner)
    label.set_text(f"{winner} won!")
    label.align(lv.ALIGN.CENTER, 0, 0)
    lv.screen_load(scr_winner)
    time.sleep(5)
    lv.screen_load(scr)

def run_singleplayer_game():
    global select,position
    print("Starting SinglePlayer game...")
    scrCounter = 0
    screenArray = []
    g = Game(singleplayer=True)
    turn = RED
    position = 0
    try:
        while True:
            position = column_selection()
            screen=g.printBoard(position,turn)
            screenArray.append(screen)
            scrCounter+=1
            for i in range(scrCounter - 1):
                screenArray[i].clean()
            if select.value()==0:
                g.insert(position, turn)
                while select.value()==0:
                    pass
                turn = YELLOW if turn == RED else RED
                if g.singleplayer and turn == YELLOW:
                    turn = RED
            time.sleep(0.1)
    except Exception as e:
        show_winner_screen(str(e).split()[0])   

def run_multiplayer_game():
    global select,position
    print("Starting Multiplayer game...")
    scrCounter = 0
    screenArray = []
    g = Game()
    turn = RED
    position = 0
    try:
        while True:
            position = column_selection()
            screen=g.printBoard(position,turn)
            screenArray.append(screen)
            scrCounter+=1
            for i in range(scrCounter - 1):
                screenArray[i].clean()
            if select.value()==0:
                g.insert(position, turn)
                while select.value()==0:
                    pass
                turn = YELLOW if turn == RED else RED
            time.sleep(0.1)
    except Exception as e:
        show_winner_screen(str(e).split()[0])
    
NONE = '.'
RED = 'R'
YELLOW = 'Y'

def diagonalsPos(matrix, cols, rows):
    """Get positive diagonals, going from bottom-left to top-right."""
    for di in ([(j, i - j) for j in range(cols)] for i in range(cols + rows -1)):
        yield [matrix[i][j] for i, j in di if i >= 0 and j >= 0 and i < cols and j < rows]

def diagonalsNeg(matrix, cols, rows):
    """Get negative diagonals, going from top-left to bottom-right."""
    for di in ([(j, i - cols + j + 1) for j in range(cols)] for i in range(cols + rows - 1)):
        yield [matrix[i][j] for i, j in di if i >= 0 and j >= 0 and i < cols and j < rows]

class Game:
    def __init__(self, cols=7, rows=6, requiredToWin=4, singleplayer=False):
        """Create a new game."""
        self.cols = cols
        self.rows = rows
        self.win = requiredToWin
        self.singleplayer = singleplayer
        self.board = [[NONE] * rows for _ in range(cols)]

    def insert(self, column, color):
        """Insert the color in the given column."""
        c = self.board[column]
        if c[0] != NONE:
            raise Exception('Column is full')

        i = -1
        while c[i] != NONE:
            i -= 1
        c[i] = color

        self.checkForWin()

        if self.singleplayer and color == 'R':
            self.ai_turn()

    def ai_turn(self):
        """Make the AI (yellow) move."""
        # Try to win
        for col in range(self.cols):
            if self.can_win(col, YELLOW):
                self.insert(col, YELLOW)
                return
        
        # Try to block opponent's win
        for col in range(self.cols):
            if self.can_win(col, RED):
                self.insert(col, YELLOW)
                return
        
        # Play in the center column if possible
        center_col = self.cols // 2
        if self.board[center_col][0] == NONE:
            self.insert(center_col, YELLOW)
            return

        # Play a random move as a fallback
        available_columns = [col for col in range(self.cols) if self.board[col][0] == NONE]
        if available_columns:
            chosen_column = random.choice(available_columns)
            self.insert(chosen_column, YELLOW)
    
    def can_win(self, column, color):
        """Check if playing in the column can result in a win for the color."""
        # Create a temporary board to test the move
        temp_board = [col[:] for col in self.board]
        c = temp_board[column]
        if c[0] != NONE:
            return False

        i = -1
        while c[i] != NONE:
            i -= 1
        c[i] = color

        return self.checkLineForWinner(c)

    def checkForWin(self):
        """Check the current board for a winner."""
        w = self.getWinner()
        if w:
            self.printBoard(-1, NONE)
            time.sleep(1)
            if w=='R':
                raise Exception('RED won!')
            else:
                w=='YELLOW'
            raise Exception('YELLOW won!')

    def getWinner(self):
        """Get the winner on the current board."""
        lines = (
            self.board,  # columns
            zip(*self.board),  # rows
            diagonalsPos(self.board, self.cols, self.rows),  # positive diagonals
            diagonalsNeg(self.board, self.cols, self.rows)  # negative diagonals
        )

        for line in self.flatten(lines):
            winner = self.checkLineForWinner(line)
            if winner:
                return winner

    def flatten(self, lines):
        """Flatten the lines generator of generators into a single generator."""
        for line_group in lines:
            for line in line_group:
                yield line

    def checkLineForWinner(self, line):
        """Check a single line (column, row, or diagonal) for a winner."""
        count = 0
        last_color = NONE
        for color in line:
            if color == last_color and color != NONE:
                count += 1
                if count >= self.win:
                    return color
            else:
                last_color = color
                count = 1
        return None

    def printBoard(self, position, turn):
        # Create a screen object for the game
        game_scr = lv.obj()

        # Define the number of columns and rows for the grid
        grid_cols = 7
        grid_rows = 6
        cell_size = 25
        padding = 5

        # Calculate the correct size for the base object
        base_width = (cell_size + padding) * grid_cols + 2 * padding + 5
        base_height = (cell_size + padding) * grid_rows + 2 * padding + 5

        # Create a base object for the grid
        base_obj = lv.obj(game_scr)
        base_obj.set_size(base_width, base_height)
        base_obj.align(lv.ALIGN.CENTER, 0, 20)

        # Create the grid style
        style = lv.style_t()
        style.init()
        style.set_pad_all(padding)
        style.set_bg_color(lv.color_hex(0x000000))
        style.set_border_width(2)
        style.set_border_color(lv.color_hex(0xFFFFFF))

        # Create the grid style (RED)
        redStyle = lv.style_t()
        redStyle.init()
        redStyle.set_pad_all(padding)
        redStyle.set_bg_color(lv.color_hex(0xFF0000))
        redStyle.set_border_width(2)
        redStyle.set_border_color(lv.color_hex(0xFFFFFF))

        # Create the grid style (YELLOW)
        yellowStyle = lv.style_t()
        yellowStyle.init()
        yellowStyle.set_pad_all(padding)
        yellowStyle.set_bg_color(lv.color_hex(0xFFFF00))
        yellowStyle.set_border_width(2)
        yellowStyle.set_border_color(lv.color_hex(0xFFFFFF))

        # Create the grid style (SELECTION RED)
        selectRedStyle = lv.style_t()
        selectRedStyle.init()
        selectRedStyle.set_pad_all(padding)
        selectRedStyle.set_bg_color(lv.color_hex(0xD99888))
        selectRedStyle.set_border_width(2)
        selectRedStyle.set_border_color(lv.color_hex(0xFFFFFF))

        # Create the grid style (SELECTION YELLOW)
        selectYellowStyle = lv.style_t()
        selectYellowStyle.init()
        selectYellowStyle.set_pad_all(padding)
        selectYellowStyle.set_bg_color(lv.color_hex(0xCCCC66))
        selectYellowStyle.set_border_width(2)
        selectYellowStyle.set_border_color(lv.color_hex(0xFFFFFF))

        # Create grid cells
        for row in range(grid_rows):
            for col in range(grid_cols):
                cell = lv.obj(base_obj)
                cell.set_size(cell_size, cell_size)
                if col == position and row == 0 and (self.board[position][0] != 'R' and self.board[position][0] != 'Y'):
                    if(str(turn) == 'R'):
                        cell.add_style(selectRedStyle, lv.PART.MAIN)
                    if(str(turn) == 'Y'):
                        cell.add_style(selectYellowStyle, lv.PART.MAIN)
                    if(str(turn) == '.'):
                        cell.add_style(style, lv.PART.MAIN)
                elif(self.board[col][row] == 'R'):
                    cell.add_style(redStyle, lv.PART.MAIN)
                elif(self.board[col][row] == 'Y'):
                    cell.add_style(yellowStyle, lv.PART.MAIN)
                else:
                    cell.add_style(style, lv.PART.MAIN)
                cell.set_pos(col * (cell_size + padding), row * (cell_size + padding))
        lv.screen_load(game_scr)

        gc.collect()
        return game_scr

while True:
    update_button_selection()
    if(select.value()==0):
        while(select.value()==0):
            pass
        if selected_button_index == 0:
            run_singleplayer_game()
        elif selected_button_index == 1:
            run_multiplayer_game()

    # Trigger garbage collection
    gc.collect()
    time.sleep(0.1)
