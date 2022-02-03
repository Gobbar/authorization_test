from ctypes import Array
import sqlite3
import os
from os.path import sep
from sqlite3.dbapi2 import Connection, Cursor, connect
import uuid
import random
import string
import hashlib

class DataBase:
    def __init__(self, db_path: str = "db.sql") -> None:
        def create_users_table(connect: Connection) -> Array:
            cursor = connect.cursor()
            cursor.execute("""CREATE TABLE SysUsers (
                Id TEXT NOT NULL PRIMARY KEY,
                Name TEXT NOT NULL,
                Password TEXT NOT NULL,
                Salt TEXT NOT NULL,
                IsChangePass INTEGER NOT NULL)""")
            connect.commit()
            get_rand_str = lambda : "".join([random.choice(string.digits + string.ascii_letters) for _ in range(random.randint(5, 15))])
            users_array = ["Onotole", "Aleksei", "Kazimir", "Maria", "Liya", "Nikita", "Grigoriy", "Vasiliy", "Uliana"]
            users_array = map(lambda x: (x, get_rand_str()), users_array)
            users_array = [(str(uuid.uuid4()), x[0], hashlib.sha256(bytes(x[1], "utf-8")).hexdigest(), x[1]) for x in users_array]

            create_users_sql = """INSERT INTO SysUsers (Id, Name, Password, Salt, IsChangePass) VALUES (?, ?, ?, ?, 0)"""
            cursor.executemany(create_users_sql, users_array)
            connect.commit()
            return users_array
            
            
        def create_access_rights_table(table_name: str, users: Array, connect: Connection):
            cursor = connect.cursor()
            create_table_sql = """CREATE TABLE Sys{0}Rights (
                Id TEXT NOT NULL PRIMARY KEY,
                UserId TEXT NOT NULL,
                CanRead INTEGER NOT NULL,
                CanWrite INTEGER NOT NULL,
                CanDelegate INTEGER NOT NULL)"""
            cursor.execute(create_table_sql.format(table_name))
            connect.commit()

            rights_arr = []
            for i in users:
                if i[1] == "Onotole":
                    rights_arr.append((str(uuid.uuid4()), i[0], 1, 1, 1))
                    continue
                rights = (random.randint(0, 1), random.randint(0, 1), random.randint(0, 1))
                rights_arr.append( (str(uuid.uuid4()), i[0], rights[0], rights[1], rights[2]) )
            
            create_access_rights_sql = "INSERT INTO Sys{0}Rights (Id, UserId, CanRead, CanWrite, CanDelegate) VALUES (?, ?, ?, ?, ?)".format(table_name)
            cursor.executemany(create_access_rights_sql, rights_arr)
            connect.commit()

        def create_objects_table(system_objects_arr: Array, connect: Connection):
            cursor = connect.cursor()
            create_table_sql = """CREATE TABLE SysObjects (
                Id TEXT NOT NULL PRIMARY KEY,
                Name Text NOT NULL)"""
            cursor.execute(create_table_sql)
            connect.commit()

            objects_arr = []
            for system_object in system_objects_arr:
                objects_arr.append((str(uuid.uuid4()), system_object))
            
            create_system_objects_sql = "INSERT INTO SysObjects (Id, Name) VALUES (?, ?)"
            cursor.executemany(create_system_objects_sql, objects_arr)
            connect.commit()

        is_db_exists = os.path.exists("{0}{1}{2}".format(os.getcwd(), sep, db_path))
        self.connection = sqlite3.connect(db_path)
        if not(is_db_exists):
            users = create_users_table(self.connection)
            system_objects_arr = ["Test1", "Test2", "Test3", "Test4"]
            create_objects_table(system_objects_arr, self.connection)
            for system_object in system_objects_arr:
                create_access_rights_table(system_object, users, self.connection)
        
    def close(self):
        self.connection.close()

    def get_user_data(self, user: str) -> dict:
        sql = "SELECT Id, Name, Password, Salt, IsChangePass FROM SysUsers WHERE Name=(?)"
        cursor = self.connection.cursor()
        cursor.execute(sql, (user,)) 
        data = cursor.fetchall()
        if data == []:
            return {}
        data = data[0]
        data = {
            "id": data[0], 
            "name": data[1], 
            "password": data[2], 
            "salt": data[3], 
            "isChangePass": data[4]
        }
        return data
    
    def get_access_rights(self, id: str) -> dict:
        objects_sql = "SELECT Name FROM SysObjects"
        rights_sql_template = "SELECT CanRead, CanWrite, CanDelegate FROM Sys%sRights WHERE UserId=?"
        cursor = self.connection.cursor()
        cursor.execute(objects_sql)
        object_list = cursor.fetchall()
        data = {
            "length": len(object_list),
            "array": []
        }
        for system_object in object_list:
            cursor.execute(rights_sql_template % system_object[0], (id,))
            res = cursor.fetchall()[0]
            res = {
                "objectName": system_object[0],
                "canRead": res[0],
                "canWrite": res[1],
                "canDelegate": res[2]
            }
            data["array"].append(res)
        return data
    
    def check_right(self, right: str, obj: str, user: str):
        #objects_sql = "SELECT Name FROM SysObjects"
        rights_sql = "SELECT CanRead, CanWrite, CanDelegate FROM Sys%sRights WHERE UserId=?" % (obj)
        cursor = self.connection.cursor()
        userId = self.get_user_id(user)

        #cursor.execute(objects_sql)
        # object_list = cursor.fetchall()
        # data = {
        #     "length": len(object_list),
        #     "array": []
        # }
        #for system_object in object_list:
        cursor.execute(rights_sql, (userId,))
        res = cursor.fetchall()[0]
        data = {
            "CanRead": res[0],
            "CanWrite": res[1],
            "CanDelegate": res[2],
            "object": obj
        }
        return data

    def grant_right(self, right: str, obj: str, user: str, right_reciver: str, right_level: str):
        if (obj not in ["Test1", "Test2", "Test3", "Test4"]):
            return {"success": False, "data": {}, "message": "Table %s doesn't exists" % obj}
        update_rights_sql = "UPDATE Sys{0}Rights SET {1}={2} WHERE UserId=?".format(obj, right, right_level)
        res = self.check_right(right, obj, user)
        #userId = self.get_user_id(user)
        rightReciverId = self.get_user_id(right_reciver)
        if rightReciverId == "f46d58bb-d1c3-4cce-a8d3-171a6c98ac15":
            return {"success": False, "data": {}, "message": "Can't change Admin rights"}
        cursor = self.connection.cursor()
        if res[right] == 1 and res["CanDelegate"] == 1:
            cursor.execute(update_rights_sql, (rightReciverId, ))
            self.connection.commit()
            return {"success": True, "data": {}, "message": "Successfuly grant rights"}
        message = ""
        if (res["CanDelegate"] == 0):
            message = "You haven't CanDelegate right"
        else:
            message = "You haven't %s right" % right
        return {"success": False, "data": {}, "message": message}
        
    def get_user_id(self, user_name):
        userId_sql = "SELECT Id FROM SysUsers WHERE Name=?"
        cursor = self.connection.cursor()
        cursor.execute(userId_sql, (user_name,))
        res = cursor.fetchall()[0][0]
        cursor.close()
        return res