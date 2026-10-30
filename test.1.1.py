"""
Project: AP Research — Dual-Task Framework
Author: Nathan Han
Version: 9.0 (Stabilized & Optimized)
"""

from psychopy import visual, core, event, gui, data, monitors
import numpy as np
import os
from datetime import datetime

# -----------------------------
# Configuration
# -----------------------------
CONFIG = {
    'sub_id': '001',
    'monitor_gamma': 2.2,    # standard for most LCDs
    'luminance_jitter': 0.1, # ±10% brightness noise
    'task1_reversals': 12,
    'isi_duration': 0.5,     # blank screen time (s) between trials
    'full_screen': True
}

class DualTaskExperiment:
    def __init__(self):
        self._init_files()
        self._init_window()
        self.mouse = event.Mouse(visible=False, win=self.win)

    def _init_files(self):
        """Setup data saving and user dialog"""
        os.makedirs('data', exist_ok=True)
        
        dlg = gui.DlgFromDict(CONFIG, title='Dual-Task Framework v9.0')
        if not dlg.OK:
            core.quit()

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
        fname = f"data/{CONFIG['sub_id']}_dualtask_{timestamp}"

        self.exp = data.ExperimentHandler(
            name='DualTaskFramework',
            version='9.0',
            extraInfo=CONFIG,
            dataFileName=fname
        )

    def _init_window(self):
        """Creates the main PsychoPy window"""
        mon = monitors.Monitor('testMonitor')
        mon.setDistance(60)  # assume ~60cm viewing distance
        
        self.win = visual.Window(
            size=[1440, 900],
            fullscr=CONFIG['full_screen'],
            color=[0, 0, 0], colorSpace='rgb',
            monitor=mon, units='height'
        )
        self.fixation = visual.TextStim(self.win, text='+', height=0.05)

    def show_instruction(self, text):
        """Displays text and waits for spacebar without locking the OS"""
        msg = visual.TextStim(self.win, text=text, height=0.03, wrapWidth=1.2)
        event.clearEvents()
        
        while True:
            msg.draw()
            self.win.flip()
            keys = event.getKeys(keyList=['space', 'escape'])
            if 'escape' in keys:
                self.close_experiment()
            if 'space' in keys:
                break
        
        self.win.flip()
        core.wait(0.4)

    # -----------------------------
    # Task 1 — Odd-One-Out JND
    # -----------------------------
    def run_jnd_task(self):
        """Color discrimination task with bidirectional luminance jitter + ISI"""
        inst = (
            "TASK 1: CHROMATIC DISCRIMINATION\n\n"
            "Three circles appear. One differs slightly in hue.\n"
            "Use LEFT, RIGHT, or DOWN arrow keys to pick the odd one.\n\n"
            "Screen will blink between trials (ignore brightness).\n\n"
            "Press SPACE to start."
        )
        self.show_instruction(inst)

        base_hues = [0, 45, 90]  # red, orange-yellow, green tones

        for base in base_hues:
            self.show_instruction(f"Testing Region: {base}° — press SPACE")

            staircase = data.StairHandler(
                startVal=20.0, nReversals=CONFIG['task1_reversals'],
                stepSizes=[4, 2, 1, 0.5, 0.25], stepType='lin',
                nTrials=40, nUp=1, nDown=2, minVal=0.05, maxVal=60
            )
            self.exp.addLoop(staircase)

            positions = [(-0.3, 0), (0.3, 0), (0, -0.3)]
            circles = [
                visual.Circle(self.win, radius=0.1, pos=p, colorSpace='hsv')
                for p in positions
            ]

            for diff in staircase:
                # Inter-stimulus blank to prevent popout cues
                self.fixation.draw()
                self.win.flip()
                core.wait(CONFIG['isi_duration'])
                
                target = np.random.choice([0, 1, 2])
                
                # Apply true bidirectional jitter
                for i, circ in enumerate(circles):
                    jitter = np.random.uniform(-CONFIG['luminance_jitter'], CONFIG['luminance_jitter'])
                    lum = max(0.1, min(1.0, 1.0 + jitter)) # Clamp between 0.1 and 1.0
                    circ.fillColor = [base + diff, 1, lum] if i == target else [base, 1, lum]

                event.clearEvents()
                start = core.getTime()
                
                # Active wait loop to prevent OS freeze
                while True:
                    for circ in circles:
                        circ.draw()
                    self.fixation.draw()
                    self.win.flip()
                    
                    keys = event.getKeys(keyList=['left', 'right', 'down', 'escape'])
                    if keys:
                        rt = core.getTime() - start
                        if 'escape' in keys:
                            self.close_experiment()
                        break

                key_map = {'left': 0, 'right': 1, 'down': 2}
                resp = key_map[keys[0]]
                correct = int(resp == target)

                staircase.addResponse(correct)
                self.exp.addData('task', 'JND')
                self.exp.addData('base_hue', base)
                self.exp.addData('diff', diff)
                self.exp.addData('correct', correct)
                self.exp.addData('rt', rt)
                self.exp.nextEntry()

    # -----------------------------
    # Task 2 — Sorting (Cognitive Stressor)
    # -----------------------------
    def run_sorting_task(self):
        inst = (
            "TASK 2: HUE SORTING\n\n"
            "A reference color appears on the left.\n"
            "Click the closest matching color on the right.\n"
            "Press SPACE to begin."
        )
        self.show_instruction(inst)
        self.mouse.setVisible(True)

        hues = list(np.linspace(0, 120, 15))
        anchor = hues.pop(0)
        sorted_seq = [anchor]
        np.random.shuffle(hues)

        anchor_rect = visual.Rect(
            self.win, width=0.15, height=0.15, pos=(-0.5, 0.2), colorSpace='hsv'
        )

        while hues:
            options = []
            cols = 4
            start_x, start_y = -0.1, 0.3
            
            # Pre-calculate positions for this trial
            for i, h in enumerate(hues):
                x = start_x + (i % cols) * 0.2
                y = start_y - (i // cols) * 0.2
                r = visual.Rect(self.win, width=0.15, height=0.15, pos=(x, y), colorSpace='hsv')
                r.fillColor = [h, 1, 1]
                options.append((r, h, i))

            event.clearEvents()
            self.mouse.clickReset()
            start = core.getTime()
            clicked = False
            
            # Active wait loop fixes the application crash
            while not clicked:
                anchor_rect.fillColor = [anchor, 1, 1]
                anchor_rect.draw()
                
                for rect, _, _ in options:
                    rect.draw()
                    
                self.win.flip() # MUST be inside the wait loop

                if event.getKeys(['escape']):
                    self.close_experiment()

                buttons, times = self.mouse.getPressed(getTime=True)
                if buttons[0]: # Left click
                    mx, my = self.mouse.getPos()
                    for rect, hue, idx in options:
                        if rect.contains(mx, my):
                            rt = core.getTime() - start
                            anchor = hue
                            sorted_seq.append(hue)
                            hues.pop(idx)

                            self.exp.addData('task', 'Sort')
                            self.exp.addData('selected_hue', hue)
                            self.exp.addData('step', len(sorted_seq))
                            self.exp.addData('rt', rt)
                            self.exp.nextEntry()

                            clicked = True
                            
                            # Brief pause to prevent accidental double-clicks registering on the next trial
                            self.win.flip() 
                            core.wait(0.3)
                            break

        self.mouse.setVisible(False)

    # -----------------------------
    # Wrap-Up
    # -----------------------------
    def close_experiment(self):
        visual.TextStim(self.win, text="Saving data...").draw()
        self.win.flip()
        self.exp.saveAsWideText(self.exp.dataFileName + '.csv')
        self.win.close()
        core.quit()

    def run(self):
        self.run_jnd_task()
        self.run_sorting_task()

        self.show_instruction(
            "Experiment Complete.\n\nThank you for participating!\n\nPress SPACE to exit."
        )
        self.close_experiment()

if __name__ == "__main__":
    DualTaskExperiment().run()