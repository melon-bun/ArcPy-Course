import arcpy
import os
import re
#Set env para and overwrite para
arcpy.env.workspace = arcpy.GetParameterAsText(0)
arcpy.env.overwriteOutput = arcpy.GetParameterAsText(6)

#mainly para
Poly_fc = arcpy.GetParameterAsText(1)
Query = arcpy.GetParameterAsText(2)
Fieldname = arcpy.GetParameterAsText(3)
OutputGDB = arcpy.GetParameterAsText(4)

def CorrectBasename(name):
	if " " in name or "-" in name or ";" in name or "," in name:
		arcpy.AddMessage("The name is not valid")
		new = re.split(';|,|-| ',name)
		newname =  "_".join(new)
		return newname
	else:
		return name

def Selection(InputFeature, Field, OutputGDB, basename, SQL):
	cursor = arcpy.da.SearchCursor(InputFeature, Field, SQL)
	for row in cursor:
		NewQuery = "{field} = '{val}'".format(field = Field,  val = str(list(row)[0]))		
		Indiv_name = basename+"_"+str(list(row)[0])
		arcpy.AddMessage(Indiv_name)
		Outpath = os.path.join(OutputGDB,Indiv_name)
		arcpy.AddMessage(Outpath)
		arcpy.Select_analysis(InputFeature, Outpath, NewQuery)
	del cursor
	del row

OutputBasename = CorrectBasename(arcpy.GetParameterAsText(5))

try:
	Selection(Poly_fc, Fieldname, OutputGDB, OutputBasename, Query)
except:
	print (arcpy.GetMessages())



