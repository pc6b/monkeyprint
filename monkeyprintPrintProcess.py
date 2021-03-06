# -*- coding: latin-1 -*-

#	Copyright (c) 2015 Paul Bomke
#	Distributed under the GNU GPL v2.
#
#	This file is part of monkeyprint.
#
#	monkeyprint is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	monkeyprint is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You have received a copy of the GNU General Public License
#    along with monkeyprint.  If not, see <http://www.gnu.org/licenses/>.

import threading, Queue
import monkeyprintSerial
import monkeyprintCommands
import time



class printProcess(threading.Thread):

	# Init function.
	def __init__(self, modelCollection, settings, queueSliceOut, queueSliceIn, queueStatus, queueConsole, queueCarryOn=None):
	# TODO: implement hold until carry on communication with gui.
	# TODO: merge all queues into one, send tuple with [infoType, info]
		# Internalise settings.
		self.settings = settings
		self.queueSliceOut = queueSliceOut
		self.queueSliceIn = queueSliceIn
		self.queueStatus = queueStatus
		self.queueConsole = queueConsole
		
		
		self.runGCode = not self.settings['monkeyprintBoard'].value
		
		# Create GCode commands.
		if self.runGCode:
			# Create parser object.
			self.gCodeParser = monkeyprintCommands.stringEvaluator(self.settings, modelCollection)
			# Parse GCode variables.
			self.gCodeTiltCommand = self.gCodeParser.parseCommand(self.settings['Tilt GCode'].value)
			self.gCodeBuildCommand = self.gCodeParser.parseCommand(self.settings['Build platform GCode'].value)
			self.gCodeShutterOpenCommand = self.gCodeParser.parseCommand(self.settings['Shutter open GCode'].value)
			self.gCodeShutterCloseCommand = self.gCodeParser.parseCommand(self.settings['Shutter close GCode'].value)
			# Get start and end code.
			self.gCodeStartCommands = self.settings['Start commands GCode'].value
			self.gCodeEndCommands = self.settings['End commands GCode'].value
			self.gCodeHomeCommand = self.settings['Home GCode'].value
			
			print "Tilt command: " + self.gCodeTiltCommand
			print "Build command: " + self.gCodeBuildCommand
			print "Shutter open command: " + self.gCodeShutterOpenCommand
			print "Shutter close command: " + self.gCodeShutterCloseCommand
			print "Start command: " + self.gCodeStartCommands
			print "End command: " + self.gCodeEndCommands
			print "Home command: " + self.gCodeHomeCommand
		
		# Get other relevant values.
		self.numberOfSlices = modelCollection.getNumberOfSlices()
		self.buildStepsPerMm = int(360. / float(self.settings['Build step angle'].value) * float(self.settings['Build microsteps per step'].value))
		self.buildMinimumMove = int(self.buildStepsPerMm * float(self.settings['Build minimum move'].value))
		self.layerHeight = int(float(modelCollection.jobSettings['Layer height'].value) / float(self.settings['Build minimum move'].value))
		self.tiltAngle = int(float(self.settings['Tilt angle'].value) / (float(self.settings['Tilt step angle'].value) / float(self.settings['Tilt microsteps per step'].value)))
		self.tiltStepsPerTurn = int(360. / float(self.settings['Tilt step angle'].value) * float(self.settings['Tilt microsteps per step'].value))

		# Are we in debug mode?
		self.debug = self.settings['Debug'].value
		
		# Initialise stop flag.
		self.stopThread = threading.Event()
		
		# Call super class init function.
		super(printProcess, self).__init__()
		
		self.queueConsole.put("Print process initialised.")
		print "Print process initialised."
	
	# Stop the thread.	
	def stop(self):
		#self.queueStatus.put("Cancelled. Finishing current action.")
		self.queueStatus.put("stopping::")
		# Stop printer process by setting stop flag.
		self.stopThread.set()
	
	def queueSliceSend(self, sliceNumber):
		# Empty the response queue.
		if not self.queueSliceIn.empty():
			self.queueSliceIn.get();
		# Send the new slice number.
		while not self.queueSliceOut.empty():
			time.sleep(0.1)
		self.queueSliceOut.put(sliceNumber)
	
	def queueSliceRecv(self):
		while not self.queueSliceIn.qsize():
			time.sleep(0.1)
		result = self.queueSliceIn.get()
		return result
	
	def setGuiSlice(self, sliceNumber):
		# Set slice number to queue.
		self.queueSliceSend(sliceNumber)
		
		# Wait until gui acks that slice is set.
		# self.queueSliceRecv blocks until slice is set in gui.
		if self.queueSliceRecv() and self.debug:
			if sliceNumber >=0:
				print "Set slice " + str(sliceNumber) + "."
			else:
				print "Set black."
	
	# Non blocking wait function.
	def wait(self, timeInterval, trigger=False):
		timeCount = 0
		timeStart = time.time()
		index = 0
		while timeCount < timeInterval:
			# Fire the camera during exposure if desired.
			# Do not wait for ack to keep exposure time precise.
			if trigger and index == 2:
				self.queueConsole.put("   Triggering camera.")
				self.serialPrinter.send(['triggerCam', None, False, None])
			time.sleep(.1)
			timeCount = time.time() - timeStart
			index += 1
	
	
	# Listen to the carry on command queue until the carry on command is issued.
	def holdUntilConfirm(self):
		pass
		
	
	# Override run function.
	def run(self):
		# Print process:
		#	Start up projector.
		# 	Homing build platform.
		#	Start slice projection with black image.
		#	Activating projector.
		#	Tilting for bubbles.
		#	Start loop.
		
		# Find out if this is a debug session without serial and projector.
		debug = self.settings['Debug'].value
		if debug: print "Debug mode enabled."
		else: print "Debug mode disabled."
		projectorControl = True
		
		
		# Initialise printer. ################################################
		#self.queueStatus.put("Initialising print process.")
		self.queueStatus.put("preparing:nSlices:" + str(self.numberOfSlices))
		self.queueConsole.put("Initialising print process.")
		
		
		
		# Reset print parameters.
		self.slice = 1
		self.exposureTime = 5.


		# Create printer serial port.
		if not debug and not self.stopThread.isSet():
			self.queueStatus.put("preparing:connecting:")
			self.serialPrinter = monkeyprintSerial.printerStandalone(self.settings)
			if self.serialPrinter.serial == None:
				self.queueStatus.put("error:connectionFail:")
				#self.queueStatus.put("Serial port " + self.settings['Port'].value + " not found. Aborting.")
				self.queueConsole.put("Serial port " + self.settings['Port'].value + " not found. Aborting.\nMake sure your board is plugged in and you have defined the correct serial port in the settings menu.")
				print "Connection to printer not established. Aborting print process. Check your settings!"
				self.stopThread.set()
			else:
				# Send ping to test connection.
				if not self.runGCode:
					if self.serialPrinter.send(["ping", None, True, None]) == True:
						self.queueStatus.put("preparing:connectionSuccess:")
						#self.queueStatus.put("Connection to printer established.")
						print "Connection to printer established."
		
		
		# Send print parameters to printer.
		if not debug and not self.stopThread.isSet():
			if not self.runGCode:
				self.serialPrinter.send(['nSlices', self.numberOfSlices, True, None])
				self.serialPrinter.send(['buildRes', self.buildStepsPerMm, True, None])
				self.serialPrinter.send(['buildMinMove', self.buildMinimumMove, True, None])
				self.serialPrinter.send(['tiltRes', self.tiltStepsPerTurn, True, None])
				self.serialPrinter.send(['tiltAngle', self.tiltAngle, True, None])
				self.serialPrinter.send(['shttrOpnPs', self.settings['Shutter position open'].value, True, None])
				self.serialPrinter.send(['shttrClsPs', self.settings['Shutter position closed'].value, True, None])
			else:
				# Send start-up commands.
				#self.serialPrinter.send([self.gCodeStartCommands, None, False, None])
				pass
		elif not self.stopThread.isSet():
			if not self.runGCode:
				self.queueConsole.put("Debug: number of slices: " + str(self.numberOfSlices))
				self.queueConsole.put("Debug: build steps per mm: " + str(self.buildStepsPerMm))
				self.queueConsole.put("Debug: build minimum move: " + str(self.buildMinimumMove))
				self.queueConsole.put("Debug: tilt steps per turn: " + str(self.tiltStepsPerTurn))
				self.queueConsole.put("Debug: tilt angle steps: " + str(self.tiltAngle))
			else:
				print "Debug: GCode command: " + self.gCodeStartCommands

			
			
		
		# Create projector serial port.
		if not debug and not self.stopThread.isSet():
			#self.queueStatus.put("Connecting to projector...")
			self.queueStatus.put("preparing:startingProjector:")
			self.serialProjector = monkeyprintSerial.projector(self.settings)
			if self.serialProjector.serial == None:
				#self.queueStatus.put("Projector not found on port " + self.settings['Port'].value + ". Start manually.")
				self.queueStatus.put("error:projectorNotFound:")
				self.queueConsole.put("Projector not found on port " + self.settings['Port'].value + ". \nMake sure you have defined the correct serial port in the settings menu.")
				projectorControl = False
			else:
				#self.queueStatus.put("Projector started.")
				self.queueStatus.put("preparing:projectorConnected:")
		
		# Display black.
		print "setting slice"
		self.setGuiSlice(-1)
		print "slice set"
		# Activate projector.
		if not debug and projectorControl and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Activating projector.")
			#self.queueStatus.put("Activating projector.")
			self.queueStatus.put("preparing:startingProjector:")
			# Send projector command.
			self.serialProjector.activate()
		
		
		# Activate shutter servo.
		if not debug and not self.stopThread.isSet() and self.settings['Enable shutter servo'].value:
			if not self.runGCode:
				self.serialPrinter.send(["shutterClose", None, True, None])
				self.serialPrinter.send(["shutterEnable", None, True, None])
			else:
				#self.serialPrinter.send([self.gCodeShutterCloseCommand, None, False, None])
				pass
			print "Shutter enabled."
		elif not self.stopThread.isSet() and self.settings['Enable shutter servo'].value:
			if self.runGCode:
				print "Debug: GCode command: " + self.gCodeShutterCloseCommand
		
		
		# Homing build platform.
		if not debug and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Homing build platform.")
			#self.queueStatus.put("Homing build platform.")
			self.queueStatus.put("preparing:homing:")
			print "Homing build platform."
			# Send printer command.
			if not self.runGCode:
				self.serialPrinter.send(["buildHome", None, True, 240]) # Retry, wait 240 seconds.
			else:
				#self.serialPrinter.send([self.gCodeHomeCommand, None, False, None])
				pass
		elif not self.stopThread.isSet():
			if self.runGCode:
				print "Debug: GCode command: " + self.gCodeHomeCommand
		
		
		# Tilt to get rid of bubbles.
		if not debug and not self.stopThread.isSet() and self.settings['Enable tilt'].value:
			# Send info to gui.
			self.queueConsole.put("Tilting to get rid of bubbles.")
			#self.queueStatus.put("Removing bubbles.")
			self.queueStatus.put("preparing:bubbles:")
			print "Tilting to get rid of bubbles."
			# Tilt 5 times.
			for tilts in range(3):
				print "Tilting..."
				if not self.runGCode:
					self.serialPrinter.send(["tilt", None, True, 20])
				else:
					#self.serialPrinter.send([self.gCodeTiltCommand, None, False, None])
					pass
		elif not self.stopThread.isSet() and self.settings['Enable tilt'].value:
			if self.runGCode:
				print "Debug: GCode command: " + self.gCodeTiltCommand
		
		
		# Wait for resin to settle.
		if not debug and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Waiting " + str(self.settings['Resin settle time'].value) + " seconds for resin to settle.")
			#self.queueStatus.put("Waiting " + str(self.settings['Resin settle time'].value) + " seconds for resin to settle.")
			self.queueStatus.put("preparing:resinSettle:" + str(self.settings['Resin settle time'].value))
			print "Waiting " + str(self.settings['Resin settle time'].value) + " seconds for resin to settle."
			# Wait...
			self.wait(self.settings['Resin settle time'].value)


		

		# Send printing flag to printer.
		if not debug and not self.stopThread.isSet():
			if not self.runGCode:
				self.serialPrinter.send(['printingFlag', 1, True, None])
		
		# Start the print loop.
		while not self.stopThread.isSet() and self.slice < self.numberOfSlices+1:
			self.queueConsole.put("Printing slice " + str(self.slice) + ".")
			#self.queueStatus.put("Printing slice " + str(self.slice) + " of " + str(self.numberOfSlices) + ".")
			self.queueStatus.put("printing:nSlices:" + str(self.numberOfSlices))
			self.queueStatus.put("printing:slice:" + str(self.slice))
			if self.settings['runOnRaspberry'].value == True:
				print ("Current slice " + str(self.slice) + " of " + str(self.numberOfSlices) + ".")
			# Send slice number to printer.
			if not debug:
				pass
				# TODO change to new syntax: self.serialPrinter.setCurrentSlice(self.slice)
			# Get settings and adjust exposure time and tilt speed.
			# For first layer use base exposure time.
			# Use slow tilt from start.
			# Use fast tilt from 20th layer.
			if self.slice == 1:
	#			if not debug:
	#	TODO fix speed			self.serialPrinter.send(["tiltSpeed", self.settings['Tilt speed slow'].value, True, None])
				self.exposureTime = self.settings['Exposure time base'].value
				self.queueConsole.put("   Set exposure time to " + str(self.settings['Exposure time base'].value) + " s.")
			elif self.slice == 2:
				self.exposureTime = self.settings['Exposure time'].value
				self.queueConsole.put("   Set exposure time to " + str(self.settings['Exposure time'].value) + " s.")
			elif self.slice == 20:
				#TODO: slow and fast tilting.
	#			if not debug:
	#				self.serialPrinter.send(["tiltSpeed", self.settings['Tilt speed'].value, True, None])
				self.queueConsole.put("   Switched to fast tilting.")
			
			
			# Move build platform up by one layer.
			if not debug:
				self.queueConsole.put("   Moving build platform.")
				print "Moving build platform."
			
				if self.slice == 1:
					if not self.runGCode:
						self.serialPrinter.send(['buildMove', self.layerHeight, True, 20])
					else:
						#self.serialPrinter.send([self.gCodeBuildCommand, None, False, None])
						pass
				else:
					if not self.runGCode:
						self.serialPrinter.send(['buildMove', self.layerHeight, True, 20])
					else:
						#self.serialPrinter.send([self.gCodeBuildCommand, None, False, None])
						pass
			else:
				if self.runGCode:
					print "Debug: GCode command: " + self.gCodeBuildCommand

			# Waiting for resin to settle.
			if not debug and self.settings['Resin settle time'].value != 0.0:
				self.queueConsole.put("   Waiting for resin to settle.")
				print "Waiting for resin to settle."
				self.wait(self.settings['Resin settle time'].value)
				
			# Open shutter.
			if not debug and self.settings['Enable shutter servo'].value:
				self.queueConsole.put("   Opening shutter.")
				print "Opening shutter."
				if not self.runGCode:
					self.serialPrinter.send(["shutterOpen", None, True, None])
				else:
					#self.serialPrinter.send([self.gCodeShutterOpenCommand, None, False, None])
					pass
			elif self.settings['Enable shutter servo'].value:
				if self.runGCode:
					print "Debug: GCode command: " + self.gCodeShutterOpenCommand
			
			
			# Start exposure by writing slice number to queue.
			self.setGuiSlice(self.slice)
			# Wait during exposure. Wait function also fires camera trigger if necessary.
			self.wait(self.exposureTime, trigger=(not self.debug and self.settings['camTriggerWithExposure'].value))
			# Stop exposure by writing -1 to queue.
			self.setGuiSlice(-1)

			
			# Close shutter.
			if not debug and self.settings['Enable shutter servo'].value:
				self.queueConsole.put("   Closing shutter.")
				print "Closing shutter."
				if not self.runGCode:
					self.serialPrinter.send(["shutterClose", None, True, None])
				else:
					#self.serialPrinter.send([self.gCodeShutterCloseCommand, None, False, None])
					pass
			elif self.settings['Enable shutter servo'].value:
				if self.runGCode:
					print "Debug: GCode command: " + self.gCodeShutterCloseCommand
			
			# Fire the camera after exposure if desired.
			if not debug and self.settings['camTriggerAfterExposure'].value:
				self.queueConsole.put("   Triggering camera.")
				print "Triggering camera."
				self.serialPrinter.send(['triggerCam', None, False, None])
			
			# Tilt.
			if not debug and self.settings['Enable tilt'].value:
				self.queueConsole.put("   Tilting.")
				print "Tilting."
				if not self.runGCode:
					self.serialPrinter.send(['tilt', None, True, 20])
				else:
					#self.serialPrinter.send([self.gCodeTiltCommand, None, False, None])
					pass
			elif self.settings['Enable tilt'].value:
				if self.runGCode:
					print "Debug: GCode command: " + self.gCodeTiltCommand

			

			
			self.slice+=1
		
		#self.queueStatus.put("Stopping print.")
		self.queueStatus.put("stopping::")
		self.queueConsole.put("Stopping print.")
		print "Stopping print."
		
		# Display black.
		self.queueSliceSend(-1)
		
		# Disable shutter.
		if not debug and not self.stopThread.isSet()  and self.settings['Enable shutter servo'].value:
			if not self.runGCode:
				self.serialPrinter.send(["shutterDisable", None, True, None])
			print "Shutter disabled."

		
		if not debug and not self.stopThread.isSet():
			# TODO
			# Move build platform to top.
			print "Moving build platform to top."
			if not self.runGCode:
				self.serialPrinter.send(["buildTop", None, True, 240]) # Retry, wait 240 seconds.
				# Send printing stop flag to printer.
				self.serialPrinter.send(["printingFlag", 0, True, None]) # Retry, wait 240 seconds.prin
			else:
				#self.serialPrinter.send([self.gCodeHomeCommand, None, False, None])
				#self.serialPrinter.send([self.gCodeEndCommands, None, False, None])
				pass
			# Deactivate projector.
			if projectorControl and self.serialProjector != None:
				self.serialProjector.deactivate()
			# Close and delete communication ports.
			self.serialPrinter.close()
			del self.serialPrinter
			if projectorControl:
				self.serialProjector.close()
				del self.serialProjector
		elif not self.stopThread.isSet():
			if self.runGCode:
					print "Debug: GCode command: " + self.gCodeHomeCommand
					print "Debug: GCode command: " + self.gCodeEndCommands

		
		#self.queueStatus.put("Print stopped after " + str(self.slice) + " slices.")
		self.queueStatus.put("stopped:slice:"+ str(self.slice-1))
		print "Print stopped after " + str(self.slice) + " slices."
		
		time.sleep(3)
		# TODO find a good way to destroy this object.
		self.queueStatus.put("idle:slice:0")
	#	self.queueSliceSend(0)
		self.queueStatus.put("destroy")
