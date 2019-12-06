import sqlite3, random, threading, webbrowser, json
from flask import Flask, send_from_directory, request
from flask_restful import Api, Resource, reqparse
from flask_cors import CORS
from sqlite3 import Error
from HEIscore import process_request
from datetime import datetime, date

app = Flask(__name__, template_folder='web')
CORS(app, support_credentials=False)
api = Api(app)
dbName = "ProjectDallas.db";
def json_serializer(c):
    try :
        columns = []
        result = []
        for column in c.description:
            columns.append(column[0])
        for row in c.fetchall():
            temp_row = dict()
            for key, value in zip(columns, row):
                temp_row[key] = value
            result.append(temp_row)
        return result
    except:
        raise Exception('Invalid cursor provided')


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
    return conn

def select_rows(conn, query):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    print("Running query: {}".format(query))
    cur.execute(query)
    resp = json_serializer(cur)
    conn.close()
    return resp
    

class FNDDS(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("request_type")
        parser.add_argument("L1_code")
        parser.add_argument("L2_code")
        parser.add_argument("L3_code")
        parser.add_argument("L4_code")
        parser.add_argument("food_code")
        parser.add_argument("category_desc")
        args = parser.parse_args()
        print("Params Received: {}".format(args))
        query=""
        if (args["request_type"] == "" or (args["request_type"] == "item" and args["L3_code"] == "")):
                return "Missing required Params", 422
        if (args["request_type"] == "L2" and args["L1_code"] == ""):
            return "Missing required Params", 422
        if (args["request_type"] == "L3" and args["L1_code"] == "" and args["L2_code"] == ""):
                return "Missing required Params", 422
        if (args["request_type"] == "L4" and args["L1_code"] == "" and args["L2_code"] == "" and args["L3_code"] == ""):
                return "Missing required Params", 422
        if (args["request_type"] == "L1"):
            query = "SELECT DISTINCT \"Level1_description\", \"Level1_code\" from FNDDS_Master_Portions;"
        elif (args["request_type"] == "L2"):
            query = "SELECT DISTINCT \"Level2_description\", \"Level2_code\" from FNDDS_Master_Portions WHERE  Level1_code =" + args["L1_code"] + ";"
        elif (args["request_type"] == "L3"):
            query = "SELECT DISTINCT \"Level3_description\", \"Level3_code\" from FNDDS_Master_Portions WHERE  \"Level2_code\" =\"" + args["L2_code"] + "\";"
        elif (args["request_type"] == "L4"):
            query = "SELECT DISTINCT \"Level4_description\", \"Level4_code\" from FNDDS_Master_Portions WHERE  \"Level3_code\" =\"" + args["L3_code"] + "\";"
        elif (args["request_type"] == "item"):
            query = "SELECT DISTINCT \"Food_code\", \"Main_food_description\" from FNDDS_Master_Portions WHERE  \"Level4_code\" =\"" + args["L4_code"] + "\";"
        elif (args["request_type"] == "portion"):
            query = "SELECT DISTINCT \"Portion_description\", \"Portion_weight\", \"Portion_code\" from FNDDS_Master_Portions WHERE  \"Food_code\" =\"" + args["food_code"] + "\";"
        elif args["request_type"] == "food_items":
            query = "SELECT DISTINCT(\"Main food description\"), (\"Food code\") from FNDDS_Master WHERE \"WWEIA Category description\" =\"" + args["category_desc"] + "\";"
        else: 
            return "Missing required Params", 422
        conn = conn = create_connection(dbName)
        resp = select_rows(conn, query)
        return resp, 200

class Nutrition(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("food_code")
        args = parser.parse_args()
        print(args)
        query=""
        if args["food_code"] == "":
                return "Missing required Params", 422
        #query = "SELECT * from food_nutrition WHERE \"food code\" =\"" + args["food_code"] + "\";"
        query = "SELECT \"Alcohol (g)\", \"Carbohydrate (g)\", \"Cholesterol (mg)\", \"Energy (kcal)\","
        query = query + "\"Fatty acids, total monounsaturated (g)\", \"Fatty acids, total polyunsaturated (g)\", \"Fatty acids, total saturated (g)\","
        query = query + "\"Fiber, total dietary (g)\", \"Protein (g)\", \"Sugars, total (g)\", \"Total Fat (g)\", \"Water (g)\""
        query = query +"from food_nutrition WHERE \"food code\" =\"" + args["food_code"] + "\";"

        conn = conn = create_connection(dbName)
        resp = select_rows(conn, query)
        return resp, 200

class HEI(Resource):
    def get(self):
        resp = ""
        with open('web/HEIoutput.txt') as json_file:
            data = json.load(json_file)
            resp = data#json.dumps(data)
        return resp, 200
        
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("hei_req_json")
        args = parser.parse_args()
        print("Req json: {}".format(args['hei_req_json']));
        process_request(args['hei_req_json'])
        resp = "Success"
        return resp, 200

class History(Resource):
    def get(self):
        reset_query = "DELETE FROM HISTORY WHERE ts >= datetime('now', '-30 minutes');"
        conn = create_connection(dbName)
        c = conn.cursor()
        c.execute(reset_query)
        conn.commit()
        get_query = "SELECT Id, \"Category 1\", \"Category 2\", \"Category 3\", \"Category 4\", Item, Item_ID, Portion, Portion_ID, Quantity FROM History;"
        resp = select_rows(conn, get_query)
        return resp, 200
        
    def post(self):
        body_json = request.json
        table_entries = body_json.get("table_entries")
        reset_query = "DELETE FROM HISTORY;"
        base_query = "INSERT INTO History (Id, \"Category 1\", \"Category 2\", \"Category 3\", \"Category 4\", Item, Item_ID, Portion, Portion_ID, Quantity, ts) values(?,?,?,?,?,?,?,?,?,?,?);"
        conn = create_connection(dbName)
        c = conn.cursor()
        c.execute(reset_query)
        conn.commit()
        for entry in table_entries:
            c.execute(base_query, (entry.get("Id"),entry.get("Category 1"),entry.get("Category 2"),entry.get("Category 3"),entry.get("Category 4"),
                entry.get("Item"),entry.get("Item_ID"),entry.get("Portion"),entry.get("Portion_ID"),entry.get("Quantity"),datetime.now()))
        conn.commit()
        conn.close()
        resp = "Success"
        return resp, 200

    def delete(self):
        reset_query = "DELETE FROM HISTORY;"
        conn = create_connection(dbName)
        c = conn.cursor()
        c.execute(reset_query)
        conn.commit()
        conn.close()
        return "Success", 200

api.add_resource(FNDDS, "/fndds")
api.add_resource(Nutrition, "/nutrition")
api.add_resource(HEI, "/hei")
api.add_resource(History, "/history")
@app.route("/web/<string:page_name>/")
def hello(page_name):
    return send_from_directory('web', page_name)

port = 5000
url = "http://127.0.0.1:{0}/web/DailyNutrition.html".format(port)
threading.Timer(1.25, lambda: webbrowser.open(url) ).start()
app.run(port=port, debug=False)