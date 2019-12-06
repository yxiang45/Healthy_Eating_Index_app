import sqlite3 as db
import pandas as pd
import numpy as np
from sqlite3 import Error
import json
import sys
"""
They input should be a csv file in the format of (Food Code, Portion Code, Amount) without header.
Three tables (FoodWeights, FNDDSNutVal, FPED_1516) are included in a sqlite database data.db.

To calculate the HEI score:
    1. Get the edible weight in gram for each Food Code (FoodWeights)
    2. Get the FP components for each Food Code (FPED_1516)
    3. Get the nutrition value for each Food Code (FNDDSNutVal)

"""
# get the portion weight from FoodWeights by using Food Code and Portion Code
def get_weights (Food_code, Portion_code, Amount, conn):
    query = '''
        SELECT Food_code,Portion_weight 
        FROM FoodWeights 
        WHERE Food_code = {} AND Portion_code = {}
    '''.format(Food_code, Portion_code)
    weights = pd.read_sql_query(query,conn)
    weights['weights'] = weights["Portion_weight"]*Amount
    weights.drop("Portion_weight", axis = 1, inplace = True)
    return weights

# get the FP components by using food code        
def get_FP (Food_code,conn):
    query = '''
        SELECT * 
        FROM FPED_1516 
        WHERE "FOODCODE" = {}
    '''.format(Food_code)
    FP = pd.read_sql_query(query,conn)
    FP.drop('DESCRIPTION', axis = 1, inplace = True)
    FP.rename(columns = {"FOODCODE":"Food_code"},inplace = True)
    return FP

# get the nutritients for HEI calculation by using food code
def get_Nutrition (Food_code,conn):
    query = '''
        SELECT "Food code" AS Food_code, "Energy (kcal)" AS ENERC_KCAL, "Sodium (mg)" AS Sodium,
        "Fatty acids, total saturated (g)" AS SFAs, "Fatty acids, total monounsaturated (g)" AS MUFAs, "Fatty acids, total polyunsaturated (g)" AS PUFAs  
        FROM fndds_nutrient_values 
        WHERE "Food code" = {}
    '''.format(Food_code)
    Nutri = pd.read_sql_query(query,conn)
    return Nutri

# get the full nutrition by using food code
def get_full_Nutrition (Food_code,conn):
    query = '''
        SELECT * 
        FROM FNDDSNutVal
        JOIN NutDesc Using (Nutrient_code)
        WHERE "Food_code" = {}
    '''.format(Food_code)    
    F_Nutri = pd.read_sql_query(query,conn)
    return F_Nutri

# process the nutrition from dataframe to nested dict
def process_Nutrition (Nutri_map):
    Nutrition = {}
    for i in range(Nutri_map.shape[0]):
        Dec = Nutri_map['Nutrient_description'][i]
        Nutrition[Dec] = {}
        Val = Nutri_map['Nutrient_value'][i]
        Cod = Nutri_map['Nutrient_code'][i]
        Uni = Nutri_map['Unit'][i]
        Nutrition[Dec]['Value'] = Val
        Nutrition[Dec]['Code'] = Cod
        Nutrition[Dec]['Unit'] = Uni

    return Nutrition

def food_mapping(foodlist,conn):
    """
    1. Nutrient and Food Group Mapping (per 100g edible weights)
    2. convert to serving size consumed: xxx * weights /100g
    3. Then sum each FP componenet and nutrient across all foods
    """
    Food_map = pd.DataFrame()
    Nutri_map = pd.DataFrame()
    for i in range(foodlist.shape[0]):
        weights = get_weights(foodlist['Food_code'][i], foodlist['Portion_code'][i], foodlist['Amount'][i],conn)
        FP = get_FP(foodlist['Food_code'][i],conn)
        Nutri = get_Nutrition(foodlist['Food_code'][i],conn)
        full = weights.merge(FP, on = "Food_code").merge(Nutri, on = "Food_code")
        Food_map = Food_map.append(full,ignore_index = True)
        # full nutrition
        F_Nutri = get_full_Nutrition(foodlist['Food_code'][i],conn)
        F_Nutri['Nutrient_value']=F_Nutri['Nutrient_value'].apply(lambda x: x*weights['weights']/100)
        if i == 0:
            Nutri_map = F_Nutri
        else:
            Nutri_map['Nutrient_value'] = Nutri_map['Nutrient_value']+ F_Nutri['Nutrient_value']
    
    Food_converted = Food_map.copy()
    Food_converted.iloc[:,2:]=Food_converted.iloc[:,2:].multiply(Food_converted.iloc[:,1], axis = 0)/100
    Food_sum = Food_converted.iloc[:,2:].sum(axis = 0)
    Nutri_map.drop(['Food_code','Tagname'], axis=1, inplace=True)
    return Food_sum,Nutri_map

def HEI_scoring(Food_sum):
    """
    Scoring method: https://epi.grants.cancer.gov/hei/hei-2015-table1.html
    """
    HEI = {}
    # Total Fruits: Score maximum 5 for 	≥0.8 cup eq. per 1,000 kcal 
    HEI['Total_Fruits'] = {}
    Total_Fruits = Food_sum['F_TOTAL']/Food_sum['ENERC_KCAL']*1000
    HEI['Total_Fruits']['Measure'] = "{} cup eq. per 1,000 kcal".format(round(Total_Fruits,1))
    if Total_Fruits >= 0.8:
        HEI['Total_Fruits']['HEIscore'] = 5
    else:
        HEI['Total_Fruits']['HEIscore']= int(round(Total_Fruits/0.8*5))
    HEI['Total_Fruits']['Max_score'] = 5
    HEI['Total_Fruits']['Max_standard'] = ">=0.8 cup eq. per 1,000 kcal"
    HEI['Total_Fruits']['Min_standard'] = "0 cup eq. per 1,000 kcal"
    
    # Whole Fruits: Score maximum 5 for 	≥0.4 cup eq. per 1,000 kcal
    HEI['Whole_Fruits'] = {}
    Whole_Fruits = (Food_sum['F_CITMLB']+Food_sum['F_OTHER'])/Food_sum['ENERC_KCAL']*1000
    HEI['Whole_Fruits']['Measure'] = "{} cup eq. per 1,000 kcal".format(round(Whole_Fruits,1))
    if Whole_Fruits >=0.4:
        HEI['Whole_Fruits']['HEIscore'] = 5
    else:
        HEI['Whole_Fruits']['HEIscore'] = int(round(Whole_Fruits/0.5*5))
    HEI['Whole_Fruits']['Max_score'] = 5
    HEI['Whole_Fruits']['Max_standard'] = ">=0.4 cup eq. per 1,000 kcal"
    HEI['Whole_Fruits']['Min_standard'] = "0 cup eq. per 1,000 kcal"
    
    # Total Vegetables: Score maximum 5 for 		≥1.1 cup eq. per 1,000 kcal
    HEI['Total_Vegetables'] = {}
    Total_Vegetables = (Food_sum['V_TOTAL']+Food_sum['V_LEGUMES'])/Food_sum['ENERC_KCAL']*1000
    HEI['Total_Vegetables']['Measure'] = "{} cup eq. per 1,000 kcal".format(round(Total_Vegetables,1))
    if Total_Vegetables >=1.1:
        HEI['Total_Vegetables']['HEIscore'] = 5
    else:
        HEI['Total_Vegetables']['HEIscore'] = int(round(Total_Vegetables/1.1*5))
    HEI['Total_Vegetables']['Max_score'] = 5
    HEI['Total_Vegetables']['Max_standard'] = ">=1.1 cup eq. per 1,000 kcal"
    HEI['Total_Vegetables']['Min_standard'] = "0 cup eq. per 1,000 kcal"       

    #Greens and Beans: Score maximum 5 for      ≥0.2 cup eq. per 1,000 kcal
    HEI['Greens_and_Beans'] = {}
    Greens_n_Beans = (Food_sum['V_DRKGR']+Food_sum['V_LEGUMES'])/Food_sum['ENERC_KCAL']*1000
    HEI['Greens_and_Beans']['Measure']= "{} cup eq. per 1,000 kcal".format(round(Greens_n_Beans,1))
    if Greens_n_Beans >=0.2:
        HEI['Greens_and_Beans']['HEIscore'] = 5
    else:
        HEI['Greens_and_Beans']['HEIscore'] = int(round(Greens_n_Beans/0.2*5))
    HEI['Greens_and_Beans']['Max_score'] = 5
    HEI['Greens_and_Beans']['Max_standard'] = ">=0.2 cup eq. per 1,000 kcal"
    HEI['Greens_and_Beans']['Min_standard'] = "0 cup eq. per 1,000 kcal"
    
    #Whole Grains: Score maximum 10 for      ≥1.5 cup eq. per 1,000 kcal
    HEI['Whole_Grains'] = {}
    Whole_Grains = Food_sum['G_WHOLE']/Food_sum['ENERC_KCAL']*1000
    HEI['Whole_Grains']['Measure'] = "{} cup eq. per 1,000 kcal".format(round(Whole_Grains,1))
    if Whole_Grains >=1.5:
        HEI['Whole_Grains']['HEIscore'] = 10
    else:
        HEI['Whole_Grains']['HEIscore'] = int(round(Whole_Grains/1.5*10))
    HEI['Whole_Grains']['Max_score'] = 10
    HEI['Whole_Grains']['Max_standard'] = ">=1.5 cup eq. per 1,000 kcal"
    HEI['Whole_Grains']['Min_standard'] = "0 cup eq. per 1,000 kcal"
    
    #Dairy: Score maximum 10 for      ≥1.3 cup eq. per 1,000 kcal
    HEI['Dairy'] = {}
    Dairy = Food_sum['D_TOTAL']/Food_sum['ENERC_KCAL']*1000
    HEI['Dairy']['Measure'] = "{} cup eq. per 1,000 kcal".format(round(Dairy,1))
    if Dairy >=1.3:
        HEI['Dairy']['HEIscore'] = 10
    else:
        HEI['Dairy']['HEIscore'] = int(round(Dairy/1.3*10))
    HEI['Dairy']['Max_score'] = 10
    HEI['Dairy']['Max_standard'] = ">=1.3 cup eq. per 1,000 kcal"
    HEI['Dairy']['Min_standard'] = "0 cup eq. per 1,000 kcal"
    
    #Total Protein Foods: Score maximum 5 for      ≥2.5 cup eq. per 1,000 kcal
    HEI['Total_Protein_Foods'] = {}
    Total_Protein_Foods = (Food_sum['PF_TOTAL']+Food_sum['PF_LEGUMES'])/Food_sum['ENERC_KCAL']*1000
    HEI['Total_Protein_Foods']['Measure'] = "{} cup eq. per 1,000 kcal".format(round(Total_Protein_Foods,1))
    if Total_Protein_Foods >=2.5:
        HEI['Total_Protein_Foods']['HEIscore'] = 5
    else:
        HEI['Total_Protein_Foods']['HEIscore'] = int(round(Total_Protein_Foods/2.5*5))
    HEI['Total_Protein_Foods']['Max_score'] = 5
    HEI['Total_Protein_Foods']['Max_standard'] = ">=2.5 cup eq. per 1,000 kcal"
    HEI['Total_Protein_Foods']['Min_standard'] = "0 cup eq. per 1,000 kcal"
    
    #Seafood and Plant Proteins: Score maximum 5 for      ≥0.8 cup eq. per 1,000 kcal
    HEI['Seafood_and_Plant_Proteins'] = {}
    Seafood_n_Plant_Proteins = (Food_sum['PF_SEAFD_HI']+Food_sum['PF_SEAFD_LOW']+Food_sum['PF_SOY']+Food_sum['PF_NUTSDS']+Food_sum['PF_LEGUMES'])/Food_sum['ENERC_KCAL']*1000
    HEI['Seafood_and_Plant_Proteins']['Measure'] = "{} cup eq. per 1,000 kcal".format(round(Seafood_n_Plant_Proteins,1))
    if Seafood_n_Plant_Proteins >=0.8:
        HEI['Seafood_and_Plant_Proteins']['HEIscore'] = 5
    else:
        HEI['Seafood_and_Plant_Proteins']['HEIscore'] = int(round(Seafood_n_Plant_Proteins/0.8*5))
    HEI['Seafood_and_Plant_Proteins']['Max_score'] = 5
    HEI['Seafood_and_Plant_Proteins']['Max_standard'] = ">=0.8 cup eq. per 1,000 kcal"
    HEI['Seafood_and_Plant_Proteins']['Min_standard'] = "0 cup eq. per 1,000 kcal"

    #Refined Grains: Score maximum 10 for       ≤1.8 oz eq. per 1,000 kcal(≥4.3 oz eq. per 1,000 kcal)
    HEI['Refined_Grains'] = {}
    Refined_Grains = Food_sum['G_REFINED']/Food_sum['ENERC_KCAL']*1000
    HEI['Refined_Grains']['Measure'] = "{} oz eq. per 1,000 kcal".format(round(Refined_Grains,1))
    if Refined_Grains <=1.8:
        HEI['Refined_Grains']['HEIscore'] = 10
    else:
        if Refined_Grains >=4.3:
            HEI['Refined_Grains']['HEIscore'] = 0
        else:
            HEI['Refined_Grains']['HEIscore'] = int(round((Refined_Grains-4.3)/(1.8-4.3)*10))
    HEI['Refined_Grains']['Max_score'] = 10
    HEI['Refined_Grains']['Max_standard'] = "<=1.8 oz eq. per 1,000 kcal"
    HEI['Refined_Grains']['Min_standard'] = ">=4.3 oz eq. per 1,000 kcal"
    
    #Added Sugars: Score maximum 10 for      	≤6.5% of energy(≥26% of energy)
    # 16 calories for 1 tsp.eq.
    HEI['Added_Sugars'] = {}
    Added_Sugars = Food_sum['ADD_SUGARS']*16/Food_sum['ENERC_KCAL']*100
    HEI['Added_Sugars']['Measure'] = "{} % of energy".format(round(Added_Sugars,1))
    if Added_Sugars <=6.5:
        HEI['Added_Sugars']['HEIscore'] = 10
    else:
        if Added_Sugars >=26:
            HEI['Added_Sugars']['HEIscore'] = 0
        else:
            HEI['Added_Sugars']['HEIscore'] = int(round((Added_Sugars-26)/(6.5-26)*10))
    HEI['Added_Sugars']['Max_score'] = 10
    HEI['Added_Sugars']['Max_standard'] = "<=6.5% of energy"
    HEI['Added_Sugars']['Min_standard'] = ">=26% of energy"

    #Fatty Acids: Score maximum 10 for      (MUFAs + PUFAs) /SFAs≥2.5 ((MUFAs + PUFAs)/SFAs≤1.2)
    HEI['Fatty_Acids'] = {}
    Fatty_Acids = (Food_sum['MUFAs']+Food_sum['PUFAs'])/(Food_sum['SFAs'])
    HEI['Fatty_Acids']['Measure'] = "{} (MUFAs + PUFAs) /SFAs".format(round(Fatty_Acids,1))
    if Fatty_Acids >=2.5:
        HEI['Fatty_Acids']['HEIscore'] = 10
    else:
        if Fatty_Acids <=1.2:
            HEI['Fatty_Acids']['HEIscore'] = 0
        else:
            HEI['Fatty_Acids']['HEIscore'] = int(round((Fatty_Acids-1.2)/(2.5-1.2)*10))
    HEI['Fatty_Acids']['Max_score'] = 10
    HEI['Fatty_Acids']['Max_standard'] = "(MUFAs + PUFAs) /SFAs>=2.5"
    HEI['Fatty_Acids']['Min_standard'] = "(MUFAs + PUFAs)/SFAs<=1.2"

    #Sodium: Score maximum 10 for      ≤1.1 g per 1,000 kcal(≥2.0 g per 1,000 kcal)
    HEI['Sodium'] = {}
    Sodium = (Food_sum['Sodium']/1000)/Food_sum['ENERC_KCAL']*1000
    HEI['Sodium']['Measure'] = "{} g per 1,000 kcal".format(round(Sodium,1))
    if Sodium <=1.1:
        HEI['Sodium']['HEIscore'] = 10
    else:
        if Sodium >=2.0:
            HEI['Sodium']['HEIscore'] = 0
        else:
            HEI['Sodium']['HEIscore'] = int(round((Sodium-2.0)/(1.1-2.0)*10))
    HEI['Sodium']['Max_score'] = 10
    HEI['Sodium']['Max_standard'] = "<=1.1 g per 1,000 kcal"
    HEI['Sodium']['Min_standard'] = ">=2.0 g per 1,000 kcal"

    #Saturated Fats: Score maximum 10 for      ≤8% of energy(≥16% of energy)
    # 9 calories for 1 g Saturated Fat
    HEI['Saturated_Fats'] = {}
    Saturated_Fats = Food_sum['SFAs']*9/Food_sum['ENERC_KCAL']*100
    HEI['Saturated_Fats']['Measure'] = "{} % of energy".format(round(Saturated_Fats,1))
    if Saturated_Fats <=8:
        HEI['Saturated_Fats']['HEIscore'] = 10
    else:
        if Saturated_Fats >=16:
            HEI['Saturated_Fats']['HEIscore'] = 0
        else:
            HEI['Saturated_Fats']['HEIscore'] = int(round((Saturated_Fats-18)/(8-16)*10))
    HEI['Saturated_Fats']['Max_score'] = 10
    HEI['Saturated_Fats']['Max_standard'] = "<=8% of energy"
    HEI['Saturated_Fats']['Min_standard'] = ">=16% of energy"
    
    HEI_total = 0
    for key in HEI.keys():
        HEI_total+=HEI[key]['HEIscore']
    HEI['Total_HEI'] = HEI_total
       
    return HEI

def convert(o):
    if isinstance(o, np.int64): return int(o)  
    raise TypeError

def main(user_input):
    # Read the input foodlist, replace the path with your csv file path
    #foodlist = pd.read_csv('data/test.csv',names=["Food_code", "Portion_code", "Amount"], dtype ={"Food_code":"int64", "Portion_code":"int64", "Amount":"float64"} )
    
    foodlist = pd.DataFrame(user_input)
    foodlist = foodlist.astype({"Food_code":"int64", "Portion_code":"int64", "Amount":"float64"} )

    #Connect to the database, replace the path with your database path
    try:
        conn = db.connect('ProjectDallas.db')
    except Error as e:
        print(e)
    
    # get the food map Nutrition map then close the db connection
    Food_sum,Nutri_map = food_mapping(foodlist,conn)
    conn.close()
    
    # get the score
    HEI = HEI_scoring (Food_sum)
    
    #processing Nutri_map to a dict
    Nutrition = process_Nutrition (Nutri_map)
    
    # put output (HEI and Nutrition) to a dict
    # HEI can be used for any HEI RadarChart, and Nutritions can be used for BarChart
    output = {}
    output['HEI'] = HEI
    output['Nutrition'] = Nutrition

    # write to a json file
    with open('web/HEIoutput.txt', 'w', encoding='utf8', errors='ignore') as outfile:
        json.dump(output, outfile, indent = 2, default = convert)
    #print(output)
    #response = json.dumps(output, cls=NpEncoder)
    #return response

def process_request(hei_req_json):
    # Will be called from the server, takes the request json and responds with HEI data in json format
    user_input = json.loads(hei_req_json)
    main(user_input)
    #return response

class NpEncoder(json.JSONEncoder):
    # Custom class to encode NP types to json serialziable python types
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        else:
            return super(NpEncoder, self).default(obj)

if __name__=="__main__":
    #run python HEIscore.py '{"Food_code":[11112110,51101010,56205000,24167200,41812500,75220051],"Portion_code":[10205,61039,10043,64714,10205,10205],"Amount":[0.8,1,1,2,0.3,1]}'
    #with json object passed as string
    #to test
    user_input = json.loads(sys.argv[1])
    main(user_input)



