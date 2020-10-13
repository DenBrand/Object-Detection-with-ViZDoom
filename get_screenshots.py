##################################################################################
# This program enables the user to walk through ZDoom scenarios and take labeled
# screenshots, which can be used as training data for object detection algorithms.
# Moving with WASD, looking with mouse movement.
# Screenshots can be taken by pressing the E key.
# Wait at least one second between your screen captures. The last captured image
# within one second might override the previous ones.
# There will be a "doom red" coloured boundary box around the objects. 
# Screenshots will be saved in "screenshots/" (can be changed with the -S command
# line argument)
# There will also be json file storing raw positional data about the captured
# objects and their name.

# For additional options use the -h or --help argument
##################################################################################

from vizdoom import *
import cv2
from time import sleep
import argparse
import time
import os
import json

if __name__ == '__main__':

    # functionality for drawing boundary boxes
    doom_red_color = [0, 0, 203]

    def draw_bounding_box(screen_buffer, x, y, width, height, color):
        for i in range(width):
            screen_buffer[y, x + i, :] = color
            screen_buffer[y + height, x + i, :] = color

        for i in range(height):
            screen_buffer[y + i, x, :] = color
            screen_buffer[y + i, x + width, :] = color

    # read in optional scenario path
    parser = argparse.ArgumentParser(   description='play snap your shots',
                                        epilog='choices for SCREEN RESOLUTION: https://github.com/mwydmuch/ViZDoom/blob/master/doc/Types.md#screenresolution choices for SCREEN FORMAT: https://github.com/mwydmuch/ViZDoom/blob/master/doc/Types.md#-screenformat')
    parser.add_argument('-s',
                        default='detection_test_environment.wad',
                        help='path to the scenario', 
                        metavar='path',
                        dest='scenario_path')
    parser.add_argument('-S',
                        default='screenshots/',
                        help='saving location for screenshots', 
                        metavar='screen_path',
                        dest='screen_path')
    parser.add_argument('-r',
                        type=str,
                        default='RES_640X480',
                        help='screen resolution (default: %(default)s)',
                        dest='resolution')
    parser.add_argument('-f',
                        type=str,
                        default='BGR24',
                        help='screen format (default: %(default)s)',
                        dest='format')
    parser.add_argument('-w', '--weapon',
                        action='store_true',
                        help='enable weapon visibility',
                        dest='show_weapon')
    parser.add_argument('-H', '--hud',
                        action='store_true',
                        help='enable hud',
                        dest='show_hud')

    args = parser.parse_args()

    # resolve the screen resolution and the format referenced by the user strings. For example: the string
    # 'RES_640X480' actually means the attribute ScreenResolution.RES_640X480
    resolution = getattr(ScreenResolution, args.resolution)
    screen_format = getattr(ScreenFormat, args.format)
    screen_path = args.screen_path
    if not screen_path[-1] == '/':
        screen_path = screen_path + '/'

    game = DoomGame()

    # prepare some settings
    game.set_doom_scenario_path(args.scenario_path)
    game.set_render_hud(args.show_hud)
    game.set_render_weapon(args.show_weapon)

    game.set_mode(Mode.ASYNC_SPECTATOR)
    game.set_labels_buffer_enabled(True)
    game.set_screen_format(ScreenFormat.BGR24)
    game.set_screen_resolution(resolution)
    game.set_window_visible(True)
    game.set_render_all_frames(True)
    game.add_game_args("+freelook 1")
    game.add_game_args("+movebob 0")
    game.add_game_args("+sv_cheats 1")
    game.set_available_buttons([
        MOVE_RIGHT,
        MOVE_LEFT,
        MOVE_BACKWARD,
        MOVE_FORWARD,
        TURN_LEFT,
        TURN_RIGHT,
        LOOK_UP_DOWN_DELTA,
        TURN_LEFT_RIGHT_DELTA, 
        MOVE_LEFT_RIGHT_DELTA,
        USE
    ])

    game.init()

    sleep_time = 28

    use_pressed_recent = False

    print('STARTING CAPTURING SESSION')

    game.send_game_command("iddqd") # cheat code for god mode. HP is fixed at 100%
    game.new_episode()

    while not game.is_episode_finished():

        game.advance_action()
        
        # prevent client from taking screenshots every frame USE is pressed by maintaining
        # use_pressed_recent flag
        use_pressed = game.get_button(Button.USE) == 1.0
        if use_pressed:

            if not use_pressed_recent:
                
                # Take labeled screenshot
                print('*SNAP*')

                timestmp = time.strftime('%Y-%m-%d_%Hh%Mmin%Ssec', time.localtime())
                state = game.get_state()
                screen = state.screen_buffer
                labels = state.labels_buffer

                if not os.path.exists(screen_path):
                    os.mkdir(screen_path)

                # save raw image
                path = screen_path + str(timestmp) + '.png'
                if not cv2.imwrite(path, screen):
                    raise Exception("Could not write image")
                print('\traw image saved')

                data = {
                    'objects': []
                }

                if labels is not None:
                    
                    for l in state.labels:

                        print('\t' + l.object_name + '(' + str(l.object_id) + ') snapped')

                        # draw boundary box
                        draw_bounding_box(screen, l.x, l.y, l.width, l.height, doom_red_color)

                        # gather corresponding data
                        data['objects'].append({
                            'obj_id': l.object_id,
                            'obj_name': l.object_name,
                            'pos_x': l.x,
                            'pos_y': l.y,
                            'width': l.width,
                            'height': l.height
                        })

                # save labeled image
                path = screen_path + str(timestmp) + '_labeled.png'
                if not cv2.imwrite(path, screen):
                    raise Exception("Could not write image")
                print('\tlabeled image saved')

                # save corresponding json data
                path = screen_path + str(timestmp) + '.json'
                with open(path, 'x') as json_file:
                    json.dump(data, json_file, indent=4)
                    print('\tjson data saved')

                cv2.waitKey(sleep_time)

        use_pressed_recent = use_pressed

    sleep(2.0)

    game.close()
