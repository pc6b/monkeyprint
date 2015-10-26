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

import vtk
from vtk.util import numpy_support	# Functions to convert between numpy and vtk
import math
import cv2
import numpy
import random
import Image, ImageTk

import monkeyprintSettings

class modelContainer:
	def __init__(self, filename, programSettings):
	
		# Internalise data.
		self.filename = filename
		
		# Create model object.
		self.model = modelData(programSettings)

		# Create settings object.
		self.settings = monkeyprintSettings.modelSettings()
		
		# Load the model.
		if self.filename != "":
			self.model.loadInputFile(self.filename, self.settings)

	
	def update(self):
		self.model.update(self.settings)
	
	def updateSupports(self):
		pass
	
	def updateSlices(self):
		pass
	
	def getActor(self):
		return self.model.getActor()

# TODO: create an actor collection of all the actors for one model.
# This can then be added or removed with a single method.
	
	def getBoxActor(self):
		self.model.opacityBoundingBox(0.3)
		return (self.model.getBoundingBoxActor(), self.model.getBoundingBoxTextActor())
	
	def getSupportsActor(self):
		pass
	
	def getSlicesActor(self):
		pass

	def showBox(self):
		self.model.showBoundingBox()
		self.model.showBoundingBoxText()
		
	def hideBox(self):
		self.model.hideBoundingBox()
		self.model.hideBoundingBoxText()
	
	def showModel(self):
		pass
	
	def hideModel(self):
		pass
	
	def opaqueModel(self):
		self.model.opacity(1.0)
	
	def transparentModel(self):
		self.model.opacity(.5)
	
	def showOverhang(self):
		pass

	def hideOverhang(self):
		pass
	
	def showBottomPlate(self):
		pass

	def hideBottomPlate(self):
		pass
	
	def opaqueBottomPlate(self):
		pass
	
	def transparentBottomPlate(self):
		pass
			
	def showSupports(self):
		pass
	
	def hideSupports(self):
		pass
	
	def opaqueSupports(self):
		pass
	
	def transparentSupports(self):
		pass
	
	def showSlices(self):
		pass
	
	def hideSlices(self):
		pass
	

################################################################################
################################################################################
################################################################################

class modelCollection(dict):
	def __init__(self, programSettings):
		# Call super class init function.
		dict.__init__(self)
		# Internalise settings.
		self.programSettings = programSettings
		# Create current model id.
		self.currentModelId = ""
		# Load default model to fill settings for gui.
		self.add("default", "")	# Don't provide file name.
	
	# Function to retrieve id of the current model.
	def getCurrentModelId(self):
		return self.currentModelId
	
	# Function to retrieve current model.
	def getCurrentModel(self):
#		print "Returning model " + self.currentModelId + "."
		return self[self.currentModelId]
	
	# Function to change to current model.
	def setCurrentModelId(self, modelId):
		self.currentModelId = modelId
		
	# Function to retrieve a model object.
	def getModel(self, modelId):
		return self[modelId]
	
	# Add a model to the collection.
	def add(self, modelId, filename):
		self[modelId] = modelContainer(filename, self.programSettings)
		# Set new model as current model.
		self.currentModelId = modelId
	
	# Function to remove a model from the model collection
	def remove(self, modelId):
		if self[modelId]:
			del self[modelId]
	
	# Adjust view for model manipulation.
	def viewDefault(self):
		for model in self:
			self[model].opaqueModel()
			self[model].hideOverhang()
			self[model].hideBottomPlate()
			self[model].hideSupports()
			self[model].hideSlices()
	# Adjust view for support generation.
	def viewSupports(self):
		for model in self:
			self[model].transparentModel()
			self[model].showOverhang()
			self[model].showBottomPlate()
			self[model].opaqueBottomPlate()
			self[model].showSupports()
			self[model].opaqueSupports()
			self[model].hideSlices()
	# Adjust view for slicing.
	def viewSlices(self):
		for model in self:
			self[model].transparentModel()
			self[model].hideOverhang()
			self[model].showBottomPlate()
			self[model].transparentBottomPlate()
			self[model].showSupports()
			self[model].transparentSupports()
			self[model].showSlices()
	
	def viewPrint(self):
		for model in self:
			self[model].transparentModel()
			self[model].hideOverhang()
			self[model].showBottomPlate()
			self[model].transparentBottomPlate()
			self[model].showSupports()
			self[model].transparentSupports()
			self[model].showSlices()
	



################################################################################
################################################################################
################################################################################

class buildVolume:
	def __init__(self, buildVolumeSize):
		# Create build volume.
		self.buildVolume = vtk.vtkCubeSource()
		self.buildVolume.SetCenter(buildVolumeSize[0]/2.0, buildVolumeSize[1]/2.0, buildVolumeSize[2]/2.0)
		self.buildVolume.SetXLength(buildVolumeSize[0])
		self.buildVolume.SetYLength(buildVolumeSize[1])
		self.buildVolume.SetZLength(buildVolumeSize[2])

		# Build volume outline filter.
		self.outlineFilter = vtk.vtkOutlineFilter()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.outlineFilter.SetInput(self.buildVolume.GetOutput())
		else:
			self.outlineFilter.SetInputConnection(self.buildVolume.GetOutputPort())

		# Build volume outline mapper.
		self.buildVolumeMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
		    self.buildVolumeMapper.SetInput(self.outlineFilter.GetOutput())
		else:
		    self.buildVolumeMapper.SetInputConnection(self.outlineFilter.GetOutputPort())

		# Build volume outline actor.
		self.buildVolumeActor = vtk.vtkActor()
		self.buildVolumeActor.SetMapper(self.buildVolumeMapper)

	def getActor(self):
		return self.buildVolumeActor
	
	def resize(self, buildVolumeSize):
		self.buildVolume.SetCenter(buildVolumeSize[0]/2.0, buildVolumeSize[1]/2.0, buildVolumeSize[2]/2.0)
		self.buildVolume.SetXLength(buildVolumeSize[0])
		self.buildVolume.SetYLength(buildVolumeSize[1])
		self.buildVolume.SetZLength(buildVolumeSize[2])


################################################################################
################################################################################
################################################################################

class modelData:
	
	###########################################################################
	# Construction method definition. #########################################
	###########################################################################
	
	def __init__(self, programSettings):
		# Set up variables.
		self.rotationXOld = 0
		self.rotationYOld = 0
		self.rotationZOld = 0
		self.filenameStl = None
		self.programSettings = programSettings
		
		
		# Set up pipeline. ###################################################
		# Stl
		# --> Polydata
		# --> Calc normals
		# --> Scale
		# --> Move to origin
		# --> Rotate
		# --> Move to desired position.
		# --> Create overhang model.
		# --> Create support pattern lines.
		# --> Intersect support pattern lines with overhang model.
		# --> Create supports on intersection points.
		
		# Create stl source.
		self.stlReader = vtk.vtkSTLReader() # File name will be set later on when model is actually loaded.
		# Get polydata from stl file.
		self.stlPolyData = vtk.vtkPolyData
		self.stlPolyData = self.stlReader.GetOutput()
		# Calculate normals.
		self.stlPolyDataNormals = vtk.vtkPolyDataNormals()
		self.stlPolyDataNormals.SetInput(self.stlPolyData)
		self.stlPolyDataNormals.SplittingOff()	# Don't split sharp edges using feature angle.
		self.stlPolyDataNormals.ComputePointNormalsOn()
		self.stlPolyDataNormals.ComputeCellNormalsOff()
	#	stlNormals.Update()
		# Move to origin filter. Input is stl polydata.
		self.stlCenterTransform = vtk.vtkTransform() # Empty transformation matrix.
		self.stlCenterFilter = vtk.vtkTransformFilter()
		self.stlCenterFilter.SetTransform(self.stlCenterTransform)
		self.stlCenterFilter.SetInput(self.stlPolyDataNormals.GetOutput())
		# Scale filter. Input is scale filter.
		self.stlScaleTransform = vtk.vtkTransform()	# Empty transformation matrix.
		self.stlScaleFilter = vtk.vtkTransformFilter()
		self.stlScaleFilter.SetTransform(self.stlScaleTransform)
		self.stlScaleFilter.SetInput(self.stlCenterFilter.GetOutput())	# Note: stlPolyData is a data object, hence no GetOutput() method is needed.
		# Rotate filter. Input is move filter.
		self.stlRotateTransform = vtk.vtkTransform()	# Empty transformation matrix.
		self.stlRotationFilter=vtk.vtkTransformPolyDataFilter()
		self.stlRotationFilter.SetTransform(self.stlRotateTransform)
		self.stlRotationFilter.SetInputConnection(self.stlScaleFilter.GetOutputPort())
		# Move to position filter. Input is rotate filter.
		self.stlPositionTransform = vtk.vtkTransform()	# Empty transformation matrix.
		self.stlPositionFilter = vtk.vtkTransformFilter()
		self.stlPositionFilter.SetTransform(self.stlPositionTransform)
		self.stlPositionFilter.SetInput(self.stlRotationFilter.GetOutput())


		# Create stl mapper and actor. #######################################
		# Mapper.
		self.stlMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.stlMapper.SetInput(self.stlPositionFilter.GetOutput())
		else:
			self.stlMapper.SetInputConnection(self.stlPositionFilter.GetOutputPort())
		# Actor.
		self.stlActor = vtk.vtkActor()
		self.stlActor.SetMapper(self.stlMapper)
		
		
		# Model bounding box. #########################
		# Create cube.
		self.modelBoundingBox = vtk.vtkCubeSource()
		self.modelBoundingBox.SetCenter(self.getCenter())
		self.modelBoundingBox.SetXLength(self.getSize()[0])
		self.modelBoundingBox.SetYLength(self.getSize()[1])
		self.modelBoundingBox.SetZLength(self.getSize()[2])

		# Model bounding box outline filter.
		self.modelBoundingBoxOutline = vtk.vtkOutlineFilter()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.modelBoundingBoxOutline.SetInput(self.modelBoundingBox.GetOutput())
		else:
			self.modelBoundingBoxOutline.SetInputConnection(self.modelBoundingBox.GetOutputPort())

		# Model bounding box outline mapper.
		self.modelBoundingBoxMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
		    self.modelBoundingBoxMapper.SetInput(self.modelBoundingBoxOutline.GetOutput())
		else:
		    self.modelBoundingBoxMapper.SetInputConnection(self.modelBoundingBoxOutline.GetOutputPort())

		# Model bounding box outline actor.
		self.modelBoundingBoxActor = vtk.vtkActor()
		self.modelBoundingBoxActor.SetMapper(self.modelBoundingBoxMapper)
		
		# Display size as text.
		self.modelBoundingBoxTextActor = vtk.vtkCaptionActor2D()
		
		self.modelBoundingBoxTextActor.GetTextActor().SetTextScaleModeToNone()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetFontFamilyToArial()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetFontSize(11)
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetOpacity(.5)
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().ShadowOff()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().ItalicOff()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().BoldOff()
		self.modelBoundingBoxTextActor.BorderOff()
		self.modelBoundingBoxTextActor.LeaderOff()
		self.modelBoundingBoxTextActor.SetPadding(0)
		
		
		# Get volume.
		self.modelVolume = vtk.vtkMassProperties()
		self.modelVolume.SetInput(self.stlPositionFilter.GetOutput())



	# #########################################################################
	# Public method definitions. ##############################################
	# #########################################################################


	# Analyse normal Z component.
	def getNormalZComponent(self, inputPolydata):
		normalsZ = vtk.vtkFloatArray()
		normalsZ.SetNumberOfValues(inputPolydata.GetPointData().GetArray('Normals').GetNumberOfTuples())
		normalsZ.CopyComponent(0,inputPolydata.GetPointData().GetArray('Normals'),2)
		inputPolydata.GetPointData().SetScalars(normalsZ)
		return inputPolydata
	
	
	def getHeight(self):
		return self.__getBounds(self.stlPositionFilter)[5]
	
	# Load a model of given filename.
	def loadInputFile(self, filename, settings):	# Import 

		# Set filename.
#		self.filenameStl = filename
		# Load model.
		self.stlReader.SetFileName(filename)#settings.getFilename())#self.filenameStl)
		self.stlPositionFilter.Update()
		# If there are no points in 'vtkPolyData' something went wrong
		if self.stlPolyData.GetNumberOfPoints() == 0:
			print "No points found in stl file."
		else:
			print 'Model loaded successfully.'
			print '   ' + str(self.stlPolyData.GetNumberOfPoints()) + " points loaded."
			print '   ' + str(self.stlPolyData.GetNumberOfPolys()) + " polygons loaded."

		# Set up the initial model scaling, rotation and position. ###########
		# Now, all we need to do is to set up the transformation matrices.
		# Fortunately, we have a method for this. Inputs: scaling, rotX [°], rotY [°], rotZ [°], posXRel [%], posYRel [%], posZ [mm].
#		self.setTransform(modelSettings.[0], modelSettings.[1], modelSettings.[2], modelSettings.[3], modelSettings.[4], modelSettings.[5], modelSettings.[6])
		self.update(settings)

	def getSize(self):
		return self.__getSize(self.stlPositionFilter)
	
	def getVolume(self):
		self.modelVolume.Update()
		return self.modelVolume.GetVolume()
	
	def getCenter(self):
		return self.__getCenter(self.stlPositionFilter)
		
	def getBounds(self):
		return self.__getBounds(self.stlPositionFilter)
		
	def getFilename(self):
		return self.filenameStl
	
	
	def getPolydata(self):
		return self.stlPositionFilter.GetOutput()

	
	def update(self, modelSettings): #scalingFactor, rotationX, rotationY, rotationZ, positionXRel, positionYRel, positionZ):
		'''
		# Limit and cast input values.
		# Scaling factor max and positionZ max depend on orientation and scaling and will be tested later on.
		if (modelSettings['Scaling'].value < 0.00001):
			modelSettings['Scaling'].setValue(0.00001)

		if (modelSettings['RotationX'].value > 359 or modelSettings['RotationX'].value < 0):
			modelSettings['RotationX'].setValue(0)
		if (modelSettings['RotationY'].value > 359 or modelSettings['RotationY'].value < 0):
			modelSettings['RotationY'].setValue(0)
		if (modelSettings['RotationZ'].value > 359 or modelSettings['RotationZ'].value < 0):
			modelSettings['RotationZ'].setValue(0)

		if (modelSettings.['Position X'].value < 0):
			modelSettings.setPositionXYRel(0, modelSettings.['Position X'].value[1])
		elif (modelSettings.['Position X'].value > 100):
			modelSettings.setPositionXYRel(100, modelSettings.['Position X'].value[1])

		if (modelSettings.['Position X'].value[1] < 0):
			modelSettings.setPositionXYRel(modelSettings.['Position X'].value[0], 0)
		elif (modelSettings.['Position X'].value[1] > 100):
			modelSettings.setPositionXYRel(modelSettings.['Position X'].value[0], 100)

		if (modelSettings['Bottom clearance'].value < 0):
			modelSettings.setBottomClearance(0)
		'''
		
		# Move model to origin. ****
		self.stlCenterTransform.Translate(-self.__getCenter(self.stlScaleFilter)[0], -self.__getCenter(self.stlScaleFilter)[1], -self.__getCenter(self.stlScaleFilter)[2])
		self.stlCenterFilter.Update()
		
		# Rotate. ******************
		# Reset rotation.
#		print "Orientation old: " + str(self.stlRotateTransform.GetOrientation())
		self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[0], 1,0,0)
		self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[1], 0,1,0)
		self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[2], 0,0,1)
#		print "Orientation reset: " + str(self.stlRotateTransform.GetOrientation())
#		print "Orientation from settings: " + str(modelSettings.getRotationXYZ())
		# Rotate with new angles.
		self.stlRotateTransform.RotateWXYZ(modelSettings['Rotation X'].value,1,0,0)
		self.stlRotateTransform.RotateWXYZ(modelSettings['Rotation Y'].value,0,1,0)
		self.stlRotateTransform.RotateWXYZ(modelSettings['Rotation Z'].value,0,0,1)
#		print "Orientation new: " + str(self.stlRotateTransform.GetOrientation())
		# Update filter.
		self.stlRotationFilter.Update()

		# Check if scaling factor has to be adjusted to make model fit in build space.
		# Get current scaling factor.
		currentScale = self.stlScaleTransform.GetScale()[0]
		# Get current size after rotation.
		self.dimX = self.__getSize(self.stlRotationFilter)[0]
		self.dimY = self.__getSize(self.stlRotationFilter)[1]
		self.dimZ = self.__getSize(self.stlRotationFilter)[2]
		# Compare the ratio of model size to build volume size in all dimensions with each other.
		# Return smallest ratio as maximum scaling.
		smallestRatio = 1
		if (self.programSettings['buildSizeXYZ'].value[0] / self.dimX) <= (self.programSettings['buildSizeXYZ'].value[1] / self.dimY) and (self.programSettings['buildSizeXYZ'].value[0] / self.dimX) <= (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ):
			smallestRatio =  self.programSettings['buildSizeXYZ'].value[0] / self.dimX * currentScale
		elif (self.programSettings['buildSizeXYZ'].value[1] / self.dimY) <= (self.programSettings['buildSizeXYZ'].value[0] / self.dimX) and (self.programSettings['buildSizeXYZ'].value[1] / self.dimY) <= (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ):
			smallestRatio =  self.programSettings['buildSizeXYZ'].value[1] / self.dimY * currentScale
		elif (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ) <= (self.programSettings['buildSizeXYZ'].value[0] / self.dimX) and (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ) <= (self.programSettings['buildSizeXYZ'].value[1] / self.dimY):
			smallestRatio =  self.programSettings['buildSizeXYZ'].value[2] / self.dimZ * currentScale
		# Restrict input scalingFactor if necessary.
		if smallestRatio < modelSettings['Scaling'].value:
			print modelSettings['Scaling'].value
			print 'foo'
			modelSettings['Scaling'].setValue(smallestRatio)
			print smallestRatio
			print modelSettings['Scaling'].value
			
		# Scale. *******************
		# First, reset scale to 1.
		self.stlScaleTransform.Scale(1/self.stlScaleTransform.GetScale()[0], 1/self.stlScaleTransform.GetScale()[1], 1/self.stlScaleTransform.GetScale()[2])
		# Change scale value.
		self.stlScaleTransform.Scale(modelSettings['Scaling'].value, modelSettings['Scaling'].value, modelSettings['Scaling'].value)
		self.stlScaleFilter.Update()	# Update to get new bounds.

		# Position. ****************
		clearRangeX = self.programSettings['buildSizeXYZ'].value[0] - self.__getSize(self.stlRotationFilter)[0]
		clearRangeY = self.programSettings['buildSizeXYZ'].value[1] - self.__getSize(self.stlRotationFilter)[1]
		positionZMax = self.programSettings['buildSizeXYZ'].value[2] - self.__getSize(self.stlRotationFilter)[2]
		if modelSettings['Bottom clearance'].value > positionZMax:
			modelSettings['Bottom clearance'].setValue(positionZMax)
		self.stlPositionTransform.Translate(  (self.__getSize(self.stlRotationFilter)[0]/2 + clearRangeX * (modelSettings['Position X'].value / 100.0)) - self.stlPositionTransform.GetPosition()[0],      (self.__getSize(self.stlRotationFilter)[1]/2 + clearRangeY * (modelSettings['Position Y'].value / 100.0)) - self.stlPositionTransform.GetPosition()[1],       self.__getSize(self.stlRotationFilter)[2]/2 - self.stlPositionTransform.GetPosition()[2] + modelSettings['Bottom clearance'].value)
		self.stlPositionFilter.Update()

		# Recalculate normals.
		self.getNormalZComponent(self.stlPositionFilter.GetOutput())
		
		# Reposition bounding box.
		self.modelBoundingBox.SetCenter(self.getCenter())
		self.modelBoundingBox.SetXLength(self.getSize()[0])
		self.modelBoundingBox.SetYLength(self.getSize()[1])
		self.modelBoundingBox.SetZLength(self.getSize()[2])
		self.modelBoundingBoxTextActor.SetCaption("x: %6.2f mm\ny: %6.2f mm\nz: %6.2f mm\nVolume: %6.2f ml"	% (self.getSize()[0], self.getSize()[1], self.getSize()[2], self.getVolume()/1000.0) )
		self.modelBoundingBoxTextActor.SetAttachmentPoint(self.getBounds()[1], self.getBounds()[3], self.getBounds()[5])
		

	def getActor(self):
		return self.stlActor
		
	def hide(self):
		self.stlActor.SetVisibility(False)
	
	def show(self):
		self.stlActor.SetVisibility(True)
		
	def color(self, r, g, b):
		self.stlActor.GetProperty().SetColor(r,g,b)
	
	def opacity(self, opacity):
		self.stlActor.GetProperty().SetOpacity(opacity)
	
	def getBoundingBoxActor(self):
		return self.modelBoundingBoxActor
		
	def hideBoundingBox(self):
		self.modelBoundingBoxActor.SetVisibility(False)

	def showBoundingBox(self):
		self.modelBoundingBoxActor.SetVisibility(True)
		
	def colorBoundingBox(self, r, g, b):
		self.modelBoundingBoxActor.GetProperty().SetColor(r,g,b)
	
	def opacityBoundingBox(self, opacity):
		self.modelBoundingBoxActor.GetProperty().SetOpacity(opacity)
	
	def getBoundingBoxTextActor(self):
		return self.modelBoundingBoxTextActor
	
	def hideBoundingBoxText(self):
		self.modelBoundingBoxTextActor.SetVisibility(False)

	def showBoundingBoxText(self):
		self.modelBoundingBoxTextActor.SetVisibility(True)
		
	def colorBoundingBoxText(self, r, g, b):
		self.modelBoundingBoxTextActor.GetProperty().SetColor(r,g,b)
	
	def opacityBoundingBoxText(self, opacity):
		self.modelBoundingBoxTextActor.GetProperty().SetOpacity(opacity)
		
		
		
		
	###########################################################################
	# Private method definitions. #############################################
	###########################################################################
	
	def __getBounds(self, inputFilter):
		# Update filter and get bounds.
		inputFilter.Update()
		bounds = [0 for i in range(6)]
		inputFilter.GetOutput().GetBounds(bounds)
		return bounds


	def __getSize(self, inputFilter):
		# Update filter and get bounds.
		inputFilter.Update()
		bounds = self.__getBounds(inputFilter)
		size = [0 for i in range(3)]
		size[0] = bounds[1] - bounds[0]
		size[1] = bounds[3] - bounds[2]
		size[2] = bounds[5] - bounds[4]
		return size


	def __getCenter(self, inputFilter):
		# Update filter and get bounds.
		inputFilter.Update()
		bounds = self.__getBounds(inputFilter)
		size = self.__getSize(inputFilter)
		center = [0 for i in range(3)]
		center[0] = bounds[0] + size[0] / 2.0
		center[1] = bounds[2] + size[1] / 2.0
		center[2] = bounds[4] + size[2] / 2.0
		return center






