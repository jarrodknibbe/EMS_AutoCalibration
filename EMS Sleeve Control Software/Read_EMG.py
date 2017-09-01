# Functions for controlling the reading cycle of the sleeve

# IMPORTANT: There is a sleep function in the main reading cycle
# This should not have to be this long (currently 0.12s). Increase the
# transmission speed of the arduino. Send only shorts. Perhaps get the arduino
# to control the whole loop and only report back. This is a bottleneck at the
# moment.

#Import libraries
import numpy as np
import cv2
import serial
import time
import random
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt
from collections import deque
import os
import threading

# Import functions from neighboring classes
from Sleeve_Link import process_serial_data, flush_buffers, send_command, coordinate_data_queue, disconnect_EMS, kill_reading_thread, start_reading_thread, DataInstance
from File_Link import find_participant_ID_folder, initialise_file, write_to_file, write_single_line_file, file_write_queue, kill_writing_thread, start_writing_thread

#3 Modes of operation: read resistance, read EMG, write EMS
read_resistance = False
read_EMG = False
write_EMS = False

#Total gesture counters
gesture_counter = 0
total_gestures = 1

#Data array to represent sleeve - naiive storage of EMG/resistance averages
electrode_EMG = np.zeros(shape=(10,6))
electrode_resistance = np.zeros(shape=(10,5))

#Read four electrode positions at the beginning and end
#to calibrate for co-activation
def calibration_Read(upper_row, lower_row):
	coordinate_data_queue.append([upper_row+1, 1, upper_row+2, 1])
	coordinate_data_queue.append([upper_row+1, 4, upper_row+2, 4])
	
	command = str(upper_row+1) + "r " + str(1) + "t " + "0i" 
	send_command(True, command)
	command = str(upper_row+2) + "r 1t " + "1i"
	send_command(True, command)

	command = str(upper_row+1) + "r 4t 2i" 
	send_command(True, command)
	command = str(upper_row+2) + "r 4t " + "3i"
	send_command(True, command)

	time.sleep(0.15)

	coordinate_data_queue.append([lower_row-2, 1, lower_row-1, 1])
	coordinate_data_queue.append([lower_row-2, 4, lower_row-1, 4])

	command = str(lower_row-2) + "r 1t 0i" 
	send_command(True, command)
	command = str(lower_row-1) + "r 1t 1i"
	send_command(True, command)

	command = str(lower_row-2) + "r 4t 2i" 
	send_command(True, command)
	command = str(lower_row-1) + "r 4t 3i"
	send_command(True, command)

	time.sleep(0.15)

#Advanced technique with multiple EMG devices (Using 2 EMGs)
#Coordinate walk with Sleeve
#Enable neighbor consecutive reading
def gather_EMG_multi_reader(num_electrode_rows, num_electrode_cols, start_electrode_row, participant_no_, gesture_no_, upper_row, lower_row):
	print "Gathering EMG"

	#Tell Arduino we are reading EMG
	command = "4c"
	send_command(True, command)

	start_time = time.time()

	total_readings = 0

	#Read four electrode positions at the beginning and end
	#to calibrate for co-activation
	print "Reading calibration row..."
	calibration_Read(upper_row, lower_row)
	# return

	#While positive electrode row is not second last row
	for pos_row_index in range(0,9):

		#Read EMG for subsequent 2 rows, where possible
		total_neg_row = pos_row_index + 3 if pos_row_index < (num_electrode_rows-2) else pos_row_index + 2
		for neg_row_index in range(pos_row_index+1, total_neg_row):

			#2 EMG devices, to reading in steps of two
			for pos_col_index in range(0,3):

				#Read negative electrodes in steps of 2, overrunning at end of row
				for neg_col_index in range(-1, 2):#for neg_col_index in range(0,6):

					if pos_col_index == 0 and neg_col_index == -1:
						coordinate_data_queue.append([pos_row_index, pos_col_index*2, neg_row_index, 5])
					else:
						coordinate_data_queue.append([pos_row_index, pos_col_index*2, neg_row_index, (pos_col_index*2) + neg_col_index])

					if pos_col_index == 2 and neg_col_index == 1:
						coordinate_data_queue.append([pos_row_index, (pos_col_index*2)+1, neg_row_index, 0])
					else :
						coordinate_data_queue.append([pos_row_index, (pos_col_index*2)+1, neg_row_index, ((pos_col_index*2)+1) + neg_col_index])

					#Enable pos_chan EMG for (step_count*2) and (step_count*2+1)
					if pos_col_index == 0 and neg_col_index < 0:
						command = str(pos_row_index) + "r " + str(pos_col_index*2) + "t " + "0i" 
						send_command(True, command)
						command = str(neg_row_index) + "r 5t " + "1i"
						send_command(True, command)
					else:
						command = str(pos_row_index) + "r " + str(pos_col_index*2) + "t " + "0i" 
						send_command(True, command)
						command = str(neg_row_index) + "r " + str((pos_col_index*2)+neg_col_index) + "t " + "1i"
						send_command(True, command)

					#Read chan2 negative from 0 at end of loop
					if ((pos_col_index*2) + 1) == 5 and neg_col_index == 1:
						command = str(pos_row_index) + "r " + str((pos_col_index*2) + 1) + "t " + "2i"
						command2 = str(neg_row_index) + "r " + "0t " + "3i"
					else:
						command = str(pos_row_index) + "r " + str((pos_col_index*2) + 1) + "t " + "2i" 
						command2 = str(neg_row_index) + "r " + str(((pos_col_index*2) + 1) + neg_col_index) + "t " + "3i"

					total_readings += 2

					send_command(True, command)
					send_command(True, command2)

					time.sleep(0.12)

		print "Reading row " + str(pos_row_index) + "..."

		end_time = time.time()
		elapsed_time = end_time - start_time
		print "Row took ", elapsed_time, " seconds (cumulative)"

	#Read four electrode positions at the beginning and end
	#to calibrate for co-activation
	print "Reading calibration row..."
	calibration_Read(upper_row, lower_row)

	print "Gathered Sleeve EMG - Read " + str(total_readings) + "rows"

# Ensure all data from EMG reading loop has been written to file
def run_through_sleeve(num_electrode_rows, num_electrode_cols, start_electrode_row, participant_no, gesture_no, upper_row, lower_row):
	#1. Record EMG
	gather_EMG_multi_reader(num_electrode_rows, num_electrode_cols, start_electrode_row, participant_no, gesture_no, upper_row, lower_row)

	#Monitor all data transfer to ensure it has finished
	while len(file_write_queue) > 0:
		pass

	global file_write_queue
	print "Length of write queue " + str(len(file_write_queue)) + ", max size = " + str(file_write_queue.maxlen)

	print "Catching up on data reading..."
	while coordinate_data_queue or file_write_queue:
		print "still to read: " + str(len(coordinate_data_queue)) + " vals"
		print "still to write: " + str(len(file_write_queue)) + " vals"
		time.sleep(0.05)
	print "Done"

	#Display visualisation of average electrode EMG values
	time.sleep(1)

# Handle both the file writing and serial incoming reading threads
def kick_off_rw_threads():
	start_writing_thread()
	file_writing_thread = threading.Thread(target=write_to_file, args=())
	file_writing_thread.start()

	start_reading_thread()
	serial_reading_thread = threading.Thread(target=process_serial_data, args=())
	serial_reading_thread.start()

# Find the location to write the EMG data to
def setup_writing_details():
	#Calculate participant ID and open output file
	participant_ID = find_participant_ID_folder()
	initialise_file(participant_ID, 0)

# End process threads
def end_threads():
	kill_writing_thread()
	kill_reading_thread()

# Control EMG reading process
def run_EMG_Read_process(participant_no, gesture_no, num_electrode_rows, num_electrode_cols, start_electrode_row, upper_row_, lower_row_, curr_gesture_):
	print "Connected to Arduinos"
	initialise_file(participant_no, gesture_no)
	print "File Initialised"
	kick_off_rw_threads()
	print "Threads started"
	write_single_line_file("Details (curr_gesture, upper_row, lower_row) " + str(curr_gesture_) + " " + str(upper_row_) + " " + str(lower_row_))
	print "Writing study details"
	print "Running EMG read cycle"
	run_through_sleeve(num_electrode_rows, num_electrode_cols, start_electrode_row, participant_no, curr_gesture_, upper_row_, lower_row_)
	end_threads()
	
	if os.name == 'nt':
		flush_buffers()




