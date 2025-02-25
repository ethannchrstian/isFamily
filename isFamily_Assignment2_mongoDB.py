import certifi
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

# Inisialisasi koneksi ke MongoDB dengan TLS untuk keamanan
client = MongoClient(
    "mongodb+srv://ioT_isfa:d9GEtYCivP7uFY6@clusterisfa.qvcwh.mongodb.net/iot_database?retryWrites=true&w=majority",
    tlsCAFile=certifi.where()  
)
# Inisialisasi Flask app dan aktifkan CORS untuk mendukung request dari domain lain
app = Flask(__name__)
CORS(app) 

db = client["iot_database"]
sensors_collection = db["sensors1"]

@app.route('/sensor1', methods=['POST'])
def receive_sensor_data():
    """
    Menerima data sensor melalui POST request dan menyimpannya ke MongoDB.
    Hanya field 'status' yang disimpan, dengan default "No status" jika tidak ada.
    """
    data = request.json
    if not data:
        return jsonify({"message": "No data provided"}), 400

    sensor_data = {
        "status": data.get("status", "No status")
    }

    # Simpan data ke MongoDB
    sensors_collection.insert_one(sensor_data)
    
    # Hapus field '_id' jika ada, agar tidak terjadi error saat serialisasi ke JSON
    sensor_data.pop("_id", None)

    return jsonify({
        "message": "✅ Data berhasil disimpan!",
        "data": sensor_data
    }), 201

@app.route('/sensor1', methods=['GET'])
def get_sensor_data():
    '''
    Mengambil semua data sensor dari MongoDB.
    Field '_id' dikeluarkan dari hasil query agar tidak mengganggu serialisasi JSON.
    '''
    data = list(sensors_collection.find({}, {"_id": 0}))
    return jsonify(data), 200

if __name__ == '__main__':
    # Jalankan Flask agar dapat diakses melalui jaringan lokal
    app.run(host='0.0.0.0', port=5000, debug=True)
