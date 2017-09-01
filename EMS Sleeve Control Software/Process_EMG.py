# 'Class' for reading EMG data from a file and mapping to EMS data

# Import dependancies
import os
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata, Rbf
import numpy as np
from sklearn.cluster import MeanShift, estimate_bandwidth, KMeans
from sklearn.neighbors.kde import KernelDensity
from sklearn.grid_search import GridSearchCV
import scipy.signal as sg

# Import functions from neighbor files
from Sleeve_EMS import *
from Gesture_Author import run_pose_tkinter

# Global sleeve variables
num_participants = 2
num_electrodes_col = 6
num_electrodes_row = 10
data_path = os.path.join(os.getcwd(), "Data")
studyData = []
multiplier_grid = []

# -------------------------------------------
#Stacked class structure for storing participant data
class StudyData:
	def __init__(self, participant):
		self.participant = participant

class Participant:
	def __init__(self, participant_no, data):
		self.ID = participant_no
		self.data = data

class GestureInstance:
	def __init__(self, data, gesture, c_data, curr_gesture):
		self.data = data
		self.gesture = gesture
		self.calib_data = c_data
		self.gesture = curr_gesture

class DataInstance:
	def __init__(self, data, coordinates):
		self.data = data

		if len(data) > 0:
			# self.mean = np.mean(data) if np.mean(data) > 0.0 else 0.0
			#Root mean square
			self.mean = np.sqrt(np.mean(np.square(data)))
			# self.mean = (reduce(lambda x, y: x*y, data))**(1.0/len(data))
			self.std = np.std(data) # if np.std(data) > 0.0 else 0.0
			self.min = min(data)
			self.max = max(data)
			self.var = np.var(data)
			self.median = np.median(data)
		else:
			self.mean = 0
			self.std = 0
			self.min = 0
			self.max = 0
			self.var = 0
			self.median = 0

		#coordinates
		self.coords = coordinates
# -------------------------------------------

# butterworth filer
def butter_filter(datalist):
    """ Filters the data using IIR butterworth filter

        Description:
            Digital filter which returns the filtered signal using butterworth
            5th order low pass design. The cutoff frequency is 0-35Hz with 100Hz
            as sampling frequency.
        Input:
            ECGdata -- list of integers (ECG data)
        Output:
            lfilter(b,a,ECGdata)-- filtered data along one-dimension with IIR
                                      butterworth filter
    """
    fs = 200.00
    fHigh = 100.00
    fLow = 5.00
    N=4
    [b,a]=sg.butter(N,[fLow/fs, fHigh/fs], btype='band')
    global filtered
    #IIR filter
    butterdata = sg.filtfilt(b,a,datalist)
    return (abs(butterdata))

#Read EMG data in from file
def read_sensor_data(participant_ID, ID, min_row, max_row):
	global studyData
	file_name = "gesture_" + str(ID) + ".txt"
	file_path = os.path.join(data_path, "participant_" + str(participant_ID))
	try:
		f = open(os.path.join(file_path, file_name), 'r')
	except:
		return

	print "Reading: ", file_path, file_name
	data = f.readlines()
	datalist = []
	dataVals = []
	calibVals = []
	dataInstances = []
	gesture = 0
	for idx, line in enumerate(data):
		if idx == 0:
			gesture = int(line.split(" ")[4])
			print "curr_gesture number = ", gesture
			continue
		if line != "\n":
			if "Gesture" in line:
				gesture = line.split(" ")[1]
				print "gesture = " + gesture
			elif "EMG" in line:

				if idx == 2:
					print line

				splitVals = line.split(" ")
				dev_ID = int(splitVals[1])
				coordinates = [int(vals) for vals in splitVals[1:5]]
				if coordinates[0] < min_row or (coordinates[0] > max_row or coordinates[2] > max_row):
					continue
				if coordinates[3] < (coordinates[1] - 1) or coordinates[3] > (coordinates[1] + 1):
					if (coordinates[3] == 5 and coordinates[1] == 0) or (coordinates[3] == 0 and coordinates[1] == 5):
						pass
					else:
						continue

				if idx == 2:
					print splitVals
					print coordinates

				del splitVals[0:6]

				if idx == 2:
					print splitVals

				for vals in splitVals:
					vals_new = vals.strip(',').replace('[', '').replace(']','')
					try:
						if int(vals_new) < 0:
							datalist.append(int(vals_new)*-1)
						else:
							datalist.append(int(vals_new))
					except:
						pass

				datalist_butter = butter_filter(datalist)

				if idx < 5 or idx > len(data)-4:
					calibVals.append(DataInstance(datalist_butter, coordinates))
				else:
					dataVals.append(DataInstance(datalist_butter, coordinates))

				datalist = []
			else:
				splitVals = line.split(" ")
				del splitVals[-1]
				dataVals.append(DataInstance([int(i) for i in splitVals]))
				print dataVals
				if len(dataVals) == 4:
					dataInstances.append(GestureInstance(dataVals, gesture))
					dataVals = []
					gesture = ""

	#Temporary test
	dataInstances.append(GestureInstance(dataVals, "EMG", calibVals, gesture))
	participant = Participant(ID, dataInstances)
	global studyData
	studyData.append(StudyData(participant))

	f.close()

# Clear all read study data
def clear_data():
	global studyData
	studyData = []

# Make available all study data to external classes
def getData():
	global studyData
	return studyData

#Explore change in EMS over time
#Co-activating muscles don't change - active muscles increase over time
def change_over_time(participant_no):
	calib_mean = np.ones(shape=(10,6))
	calib_std = np.ones(shape=(10,6))
	read_mean = np.ones(shape=(10,6))
	read_std = np.ones(shape=(10,6))
	for data in studyData[participant_no].participant.data[0].calib_data:
		# print "data.coords = ", data.coords, ", data.mean = ", data.mean
		calib_mean[data.coords[0]][data.coords[1]] = data.mean*1.0
		calib_std[data.coords[0]][data.coords[1]] = data.std*1.0
		for data_ in studyData[participant_no].participant.data[0].data:
			if data_.coords == data.coords:
				# print "data_.coords = ", data_.coords, ", data_.mean = ", data_.mean
				read_mean[data.coords[0]][data.coords[1]] = data_.mean
				read_std[data.coords[0]][data.coords[1]] = data_.std


	np.set_printoptions(precision=2, suppress=True) #, threshold=np.inf)
	print "Calib/read means = ", (calib_mean / read_mean)
	print "Calib/read stds = ", (calib_std / read_std)
	# print read_mean, calib_mean

	np_mask = calib_mean / read_mean
	x = []
	y = []
	z = []
	for i in range(0,10):
		for j in range(0,6):
			if np_mask[i][j] != 1.0:
				x.append(j)
				y.append(i)
				if np_mask[i][j] == np.inf:
					z.append(1)
				else:
					z.append(np_mask[i][j])

	print x, y, z

	ti = np.linspace(0, 10, 6)
	ti_ = np.linspace(0,10,10)
	XI, YI = np.meshgrid(ti_,ti)
	rbf = Rbf(x, y, z, function='linear')
	global multiplier_grid
	multiplier_grid = rbf(XI, YI)

	print multiplier_grid
	return

#Subtract resting data from participant data to get normalised activation
def normalise_participant(participant_no):
	global studyData, multiplier_grid
	rest_participant = 0
	for data in studyData[participant_no].participant.data[0].data:
		for rest_data in studyData[rest_participant].participant.data[0].data:
			if data.coords[0] == rest_data.coords[0] and data.coords[1] == rest_data.coords[1] \
				and data.coords[2] == rest_data.coords[2] and data.coords[3] == rest_data.coords[3]:
				#data.data = [a-b for a,b in zip(data.data, rest_data.data)]
				data.data[:] = [max(x - (rest_data.mean + rest_data.std), 0.0) for x in data.data]
				# data.data[:] = [x - (rest_data.mean) for x in data.data]

				data.mean -= rest_data.mean
				if data.mean < 0.0:
				 	data.mean = 0.0
				 	# data.mean *= -1.0
				data.std -= rest_data.std
				data.std = max(data.std, 0.0)
				data.max -= rest_data.max
				data.max = max(data.max, 0.0)

	# for data in studyData[participant_no].participant.data[0].data:
	# 	data.mean = data.mean * multiplier_grid[data.coords[1], data.coords[0]]
	# 	data.std = data.std * multiplier_grid[data.coords[1], data.coords[0]]
	# 	data.max = data.max * multiplier_grid[data.coords[1], data.coords[0]]

	# for data in studyData[participant_no].participant.data[0].data:
		# print data.coords, data.mean, data.std, data.max

# Grab maxs, averages, and std. dev. of all data
def grab_maxs_means(participant_no):
	maxs = []
	means = []
	stds = []
	curr_coords = []

	maxs.append([x.max for x in studyData[participant_no].participant.data[0].data])
	means.append([x.mean for x in studyData[participant_no].participant.data[0].data])
	stds.append([x.std for x in studyData[participant_no].participant.data[0].data])
	curr_coords.append([x.coords for x in studyData[participant_no].participant.data[0].data])

	return maxs, means, stds, curr_coords

# Use k-means clustering to group regions of similar activity
def cluster_vals(maxs, means, stds):
	#Prep data to correct format
	means_ = np.asarray(means)
	maxs_ = np.asarray(maxs)
	stds_ = np.asarray(stds)
	means_scatter = np.vstack((means_.ravel(), stds_.ravel(), maxs_.ravel())).T

	# #Run KMeans
	y_pred = KMeans(n_clusters=3).fit_predict(means_scatter)

	np.set_printoptions(precision=2, suppress=True) #, threshold=np.inf)

	return means_scatter, y_pred, 3

# Match clusters to ENG coordinates
def lookup_coords(participant_no, scatter, categories, num_clusters, coords):
	#sorted_cats = zip(categories, scatter) #[categories for categories, scatter in sorted(zip(categories, scatter))]
	#cluster results of kmeans
	# print categories

	# print scatter, categories

	#sort results of the clustering (index values)
	sorted_cats = categories.argsort()
	# print sorted_cats

	sorted_cats_ = np.reshape(categories, (-1, len(categories)))
	unsort_scatter = np.hstack((scatter, sorted_cats_.T))

	np_coords = np.asarray(coords)

	# print unsort_scatter.shape, np_coords.shape
	unsort_scatter = np.hstack((unsort_scatter, np_coords[0]))

	sorted_scatter = unsort_scatter[unsort_scatter[:, 3].argsort()]
	# print sorted_scatter
	# for idx, val in enumerate(coords):
	# 	unsort_scatter[idx].append(val)

	# print unsort_scatter

	return sorted_scatter

	# #sort cluster groups descending
	# sorted_cats_ = categories[sorted_cats[::-1]]
	# print sorted_cats_

	# #sort means/std. dev input data according to categories (index)
	# sorted_scatter = scatter[sorted_cats[::-1]]
	# print sorted_scatter

	# #reshape so you can append classification to mean/max data
	# sorted_cats_ = np.reshape(sorted_cats_, (-1, len(sorted_cats_)))
	# print "reshaped", sorted_cats_

	# #append classification to mean/std. dev.
	# sorted_scatter = np.hstack((sorted_scatter, sorted_cats_.T))
	# print sorted_scatter
	# sorted_coords = []

	# print coords, sorted_cats

	# # print len(sorted_cats)
	# # print len(coords[0])

	# #Match coordinates in data to kmeans results
	# for indexes in sorted_cats:
	# 	# print indexes
	# 	# print studyData[participant_no].participant.data[0].data[indexes].coords
	# 	sorted_coords.append(coords[0][indexes])
	# 	# sorted_coords.append(studyData[participant_no].participant.data[0].data[indexes].coords)

	# # for scat in sorted_scatter:
	# # 	for data in studyData[participant_no].participant.data[0].data:
	# # 		if scat[0] == data.std and scat[1] == data.mean:
	# # 			sorted_coords.append(data.coords)

	# sorted_coords_ = np.asarray(sorted_coords)

	# # print "sorted_coords", sorted_coords

	# # print len(sorted_scatter), len(sorted_coords_)

	# sorted_scatter = np.hstack((sorted_scatter, sorted_coords_))

	# # print "sorted_scatter pre = ", (sorted_scatter)

	# sorted_scatter = sorted_scatter[sorted_scatter[:, 2].argsort()]

	# np.set_printoptions(precision=2, suppress=True)
	# # print "sorted_scatter post = ", (sorted_scatter)

	# return sorted_scatter

# Calculatea stimulus amounts per cluster
def calculate_stimulus(sorted_scatter, kmeans=True):

	print "calc stimulus, scatter ", sorted_scatter
	
	#Initialise arrays that are the (no. of clusters) in size
	if kmeans:
		average_vals = [0.0] * (max(sorted_scatter[:,3])+1) #,0.0,0.0]
	else:
		average_vals = [0.0] * (max(sorted_scatter[:,2])+1)
	cluster_size = [0.0] * len(average_vals)

	print "average_vals ", average_vals

	#Add all values from categories
	for line in sorted_scatter:
		if kmeans:
			average_vals[int(line[3])] += line[1]
			cluster_size[int(line[3])] += 1
		else:
			average_vals[int(line[2])] += line[0]
			cluster_size[int(line[2])] += 1

	#Scale averages for all channels between 0 and 1
	average_vals = [average_vals/cluster_size for average_vals, cluster_size in zip(average_vals, cluster_size)]
	average_vals = [vals-min(average_vals) for vals in average_vals]
	average_vals = [vals/max(average_vals) for vals in average_vals]

	return average_vals

# Assign coordinates to the stimulation parameters
def find_stim_coords(sorted_scatter, stim_vals, kmeans=True):
	#Create array to hold stimulation points, initialise to size
	stim_points = []
	if kmeans:
		for iters in range(0,int(max(sorted_scatter[:,3])+1)):
			stim_points.append([])
	else:
		for iters in range(0,int(max(sorted_scatter[:,2])+1)):
			stim_points.append([])

	#Add coordinate to stim channel list
	for line in sorted_scatter:
		if kmeans:
			stim_points[int(line[3])].append(line[4::].tolist())
		else:
			stim_points[int(line[2])].append(line[3::].tolist())

	#sort by stim vals - 0 -> 2
	comp_array = zip(stim_vals, stim_points)
	comp_array.sort(key = lambda t: t[0])
	# print "comp array", comp_array

	stim_points = [row[1] for row in comp_array]
	stim_vals = [row[0] for row in comp_array]

	# print "stim points", stim_points
	# print "stim props", stim_vals	

	#Sort stim points to remove duplicates
	#stim_points = reduce_stim_points(stim_vals, stim_points)
	#return [],[]

	print '*' * 20
	print "kmeans" if kmeans else "kernel"
	for i in range(1,len(stim_vals)):
		print "Stim Val " + str(stim_vals[i]) + ": " + str(stim_points[i])
		print ""
	print '*' * 20

	stim_vals_norm = []

	for stim_val in stim_vals:
		if stim_val > 0.0:
			stim_vals_norm.append(int(math.floor(stim_val) + 1.0))
		else:
			stim_vals_norm.append(int(0))

	print "stim vals normalised", stim_vals_norm

	return stim_points, stim_vals, stim_vals_norm

#Currently crunching individual data
def read_and_crunch_data(participant_no, total_gestures, min_stim_row, max_stim_row, style):

	global studyData
	studyData = []

	print "Processing EMG: ", participant_no, total_gestures

	if style == 0:
		min_stim_row = 0
		max_stim_row = 10

	#read gesture data from file
	# for poses in range(1,total_gestures+1):
	for poses in [0,total_gestures]:
	# for poses in range(0,total_gestures):
		read_sensor_data(participant_no, poses, min_stim_row, max_stim_row)
		if poses > 0:
			change_over_time(1)
			normalise_participant(1)

	stim_points_all = []
	stim_proportions_all = []
	stim_proportions_norm_all = []

	#create array of gesture means and std devs
	maxs, means, stds, coords = grab_maxs_means(1)

	#cluster vals using k-means clustering
	scatter, kmeans, km_cluster = cluster_vals(maxs, means, stds)
	#match kmeans clusters to EMG coordinates
	sorted_scatter = lookup_coords(gesture, scatter, kmeans, km_cluster, coords)
	#Calculate stimulus amounts per cluster
	stim_proportions = calculate_stimulus(sorted_scatter)
	#Assign coordinates to stimulation params
	stim_points, stim_proportions, stim_proportions_norm = find_stim_coords(sorted_scatter, stim_proportions)

	#Append stim amounts and locations to global list
	stim_points_all.append(stim_points)
	stim_proportions_all.append(stim_proportions)
	stim_proportions_norm_all.append(stim_proportions_norm)

	print "Done gesture", gesture
	return stim_points_all, stim_proportions_all, stim_proportions_norm_all





