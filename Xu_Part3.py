import arcpy
import os
arcpy.AddMessage ("Library Import Complete")
intermediate = [] #this list is used to trace all intermediate result
def HighCrashRate_BlockGroup(Para_Workspace, Para_Blockgroups, Para_CountyBoundary, Para_MajorRoad, Para_Crash, Para_Distance):
    global intermediate
    local_intermediate = []
    ## Calculate the road length for each block
    arcpy.MakeFeatureLayer_management(Para_Blockgroups,"blockgroups")
    arcpy.SelectLayerByLocation_management("blockgroups","HAVE_THEIR_CENTER_IN",Para_CountyBoundary,"","NEW_SELECTION")
    arcpy.CopyFeatures_management("blockgroups","M_blg")
    arcpy.Intersect_analysis(["M_blg",Para_MajorRoad],"M_mjr_seg")
    statsFields = [["Shape_Length", "SUM"]]
    arcpy.AddMessage ("complete")
    arcpy.Statistics_analysis("M_mjr_seg", "M_mjr_seg_stat", statsFields, "FID_M_blg")
    arcpy.AddField_management("M_mjr_seg_stat", "Miles","FLOAT")
    arcpy.CalculateField_management("M_mjr_seg_stat", "Miles", '!SUM_Shape_Length! * 0.000621371192')
    JoinField = ["SUM_Shape_Length","Miles"]
    arcpy.JoinField_management("M_blg","OBJECTID","M_mjr_seg_stat","FID_M_blg", JoinField)

    ## Calculate the crash rate for each block
    arcpy.Buffer_analysis(Para_MajorRoad, "major_roads_Buffer", Para_Distance)
    arcpy.Clip_analysis(Para_Crash,"major_roads_Buffer","crashes_300feet")
    arcpy.SpatialJoin_analysis("M_blg","crashes_300feet", "M_blg_crashcount","JOIN_ONE_TO_ONE")
    arcpy.AddField_management("M_blg_crashcount","crash_rate","FLOAT")
    arcpy.CalculateField_management("M_blg_crashcount","crash_rate",'!Join_Count!/!Miles!')
    arcpy.AddMessage ("crash rate compute complete")
    crash_rate_statField = [["crash_rate","MEAN"],["crash_rate","MIN"],["crash_rate","MAX"]]
    arcpy.Statistics_analysis("M_blg_crashcount","M_blg_crashcount_stat",crash_rate_statField)

    new_item = []
    for item in ["MEAN","MIN","MAX"]:
        new_item.append(item+"_crash_rate")

    Stat_list = list(arcpy.da.SearchCursor("M_blg_crashcount_stat",new_item))

    LowRate = Stat_list[0][1]
    MidRate = (Stat_list[0][0]+Stat_list[0][1])/2
    HighRate = (Stat_list[0][1]+Stat_list[0][2])/2
    SQL_highrate = '"crash_rate" > {value}'.format(value = HighRate)
    arcpy.FeatureClassToFeatureClass_conversion("M_blg_crashcount",Para_Workspace,"HighCrashRate",SQL_highrate)
    arcpy.AddMessage ("Complete the Part 1: HighCrashRate_BlockGroup")
    local_intermediate = ["M_blg","M_mjr_seg","M_mjr_seg_stat","major_roads_Buffer","crashes_300feet","M_blg_crashcount","M_blg_crashcount_stat","HighCrashRate"]
    intermediate = intermediate + local_intermediate

def SuitableAreas(Para_SQL_res, Para_SQL_com, Para_school, Para_hospital, Para_Workspace, Para_Landuse, Reclassification_Type, WeightRes, WeightCom, WeightSch, WeightHos):
    global intermediate
    local_intermediate = []    
    ### Calculate the buffer of residental and commerical block
    SQL_residental = Para_SQL_res
    SQL_commerical = Para_SQL_com
    arcpy.FeatureClassToFeatureClass_conversion(Para_Landuse,Para_Workspace,"Residental",Para_SQL_res)
    arcpy.FeatureClassToFeatureClass_conversion(Para_Landuse,Para_Workspace,"Commerical",Para_SQL_com)
    local_intermediate = local_intermediate + ["Residental","Commerical"]

    arcpy.AddMessage ("Identify the residental and commerical land...")
    Para_res = os.path.join(Para_Workspace,"Residental")
    Para_com = os.path.join(Para_Workspace,"Commerical")
    Raster_List = [Para_res,Para_com,Para_school,Para_hospital]

    outEucDistance = arcpy.sa.EucDistance(Para_res)
    outEucDistance.save("res_Ed")
    arcpy.AddMessage ("Euclid Distance Complete")
    outEucDistance = arcpy.sa.EucDistance(Para_com)
    outEucDistance.save("com_Ed")
    arcpy.AddMessage ("Euclid Distance Complete")
    outEucDistance = arcpy.sa.EucDistance(Para_school)
    outEucDistance.save("school_Ed")
    arcpy.AddMessage ("Euclid Distance Complete")
    outEucDistance = arcpy.sa.EucDistance(Para_hospital)
    outEucDistance.save("hosptial_Ed")
    arcpy.AddMessage ("Euclid Distance Complete")

    ### Reclass the distance
    numberZone = 9
    Slice_method = Reclassification_Type
    New_raster_list = ["res_Ed","com_Ed","school_Ed","hosptial_Ed"]
    local_intermediate = local_intermediate + New_raster_list
    calraster_list = []
    for rs in New_raster_list:
        rec_rs_name = rs.replace("_Ed","_Reclass2")
        outSlice = arcpy.sa.Slice(os.path.join(Para_Workspace,rs), numberZone,Slice_method)
        outSlice.save(rec_rs_name)
        calraster_list.append(rec_rs_name)
        local_intermediate.append(rec_rs_name)
        arcpy.AddMessage ("Reclassification Complete")
    #     acrpy.AddMessage(3)
    #     rec_rs_name = rs.replace("_Ed","_Reclass2")
    #     calraster_list.append(rec_rs_name)
    #     acrpy.AddMessage(3)
    #     outSlice = arcpy.sa.Slice(rs, numberZone,Slice_method)
    #     outSlice.save(rec_rs_name)
    #     arcpy.AddMessage (2)
    # arcpy.AddMessage (calraster_list)
    # outSlice = arcpy.sa.Slice(os.path.join(Para_Workspace,"res_Ed"), numberZone,Slice_method)
    # outSlice.save("res_Reclass")

    ### Calculate the raster
    weight_res = float(WeightRes)/100
    weight_com = float(WeightCom)/100
    weight_school = float(WeightSch)/100
    weight_hospital = float(WeightHos)/100
    calraster = arcpy.sa.Raster(os.path.join(Para_Workspace,calraster_list[0]))*weight_res+arcpy.sa.Raster(os.path.join(Para_Workspace,calraster_list[1]))*weight_com+arcpy.sa.Raster(os.path.join(Para_Workspace,calraster_list[2]))*weight_school+(10-arcpy.sa.Raster(os.path.join(Para_Workspace,calraster_list[3])))*weight_hospital
    arcpy.AddMessage ("Raster Calculate Complete")
    calraster = arcpy.sa.Int(calraster)
    arcpy.AddMessage ("Convert float raster to integer raster")
    arcpy.AddMessage ("Saving the final raster...")
    calraster.save("FinalRaster")
    
    ### Raster to Polygon
    Para_Suitablearea = os.path.join(Para_Workspace,"Suitable_Area")
    Para_FinalRaster = os.path.join(Para_Workspace,"FinalRaster")
    arcpy.RasterToPolygon_conversion(Para_FinalRaster,Para_Suitablearea)
    SQL_high_value = "gridcode = 1"
    arcpy.FeatureClassToFeatureClass_conversion(Para_Suitablearea,Para_Workspace,"HighValue",SQL_high_value)    
    arcpy.AddMessage  ("Complete the Part 2: Most Suitable Areas")
    local_intermediate = local_intermediate + ["Suitable_Area","FinalRaster","HighValue"]
    intermediate = intermediate +local_intermediate

def TheFinalResult(Para_OutputGDB, Para_OutputName,intermediate_list):
    if Para_OutputName in intermediate_list:
        Para_OutputName = "New_"+Para_OutputName
    arcpy.Intersect_analysis(["HighValue","HighCrashRate"],"OverlapArea")
    arcpy.JoinField_management("HighCrashRate","OBJECTID","OverlapArea","FID_HighCrashRate", "Shape_Area")
    arcpy.FeatureClassToFeatureClass_conversion("HighCrashRate",Para_OutputGDB,Para_OutputName,"Shape_Area_12 > ( 0.5 * Shape_Area)")
    arcpy.AddMessage ("Complete the Part 3: The Final Result")

def TheCleanWork(intermediate_list):
    arcpy.AddMessage("Delete the intermediate...")
    for element in intermediate_list:
        arcpy.Delete_management(element)
        arcpy.AddMessage("Delete {0}".format(element))

arcpy.env.workspace = arcpy.GetParameterAsText(10)
WorkPlacePath = arcpy.GetParameterAsText(10)
COUNTY_BOUNDARY = arcpy.GetParameterAsText(1)
BLOCK_GROUP = arcpy.GetParameterAsText(2)
MAJOR_ROADS = arcpy.GetParameterAsText(3)
CRASH = arcpy.GetParameterAsText(4)
LANDUSE = arcpy.GetParameterAsText(5)
SQL_RES = arcpy.GetParameterAsText(6)
SQL_COM = arcpy.GetParameterAsText(7)
SCHOOLS = arcpy.GetParameterAsText(8)
HOSPITALS = arcpy.GetParameterAsText(9)
OutputPath = arcpy.GetParameterAsText(10)
OutputName = arcpy.GetParameterAsText(11)
if arcpy.GetParameterAsText(12) == "True":
	arcpy.env.overwriteOutput = True
arcpy.env.extent = arcpy.GetParameterAsText(13)
arcpy.env.mask = arcpy.GetParameterAsText(13)
arcpy.env.cellSize = int(arcpy.GetParameterAsText(14))
WEIGHT_RES = arcpy.GetParameterAsText(15)
WEIGHT_COM = arcpy.GetParameterAsText(16)
WEIGHT_SCHOOLS = arcpy.GetParameterAsText(17)
WEIGHT_HOSPITALS = arcpy.GetParameterAsText(18)
Buffer_DISTANCE = arcpy.GetParameterAsText(19)
RECLASS_TYPE = arcpy.GetParameterAsText(20)

try:
    HighCrashRate_BlockGroup(WorkPlacePath, BLOCK_GROUP,COUNTY_BOUNDARY,MAJOR_ROADS,CRASH,Buffer_DISTANCE)
    SuitableAreas(SQL_RES,SQL_COM,SCHOOLS,HOSPITALS,WorkPlacePath,LANDUSE,RECLASS_TYPE,WEIGHT_RES,WEIGHT_COM,WEIGHT_SCHOOLS,WEIGHT_HOSPITALS)
    TheFinalResult(OutputPath,OutputName,intermediate)
    TheCleanWork(intermediate)
except:
    print (arcpy.GetMessages())

