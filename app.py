from flask import Flask, render_template
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import boto3
import os

load_dotenv()
app = Flask(__name__)

# MongoDB
client = MongoClient(os.getenv("MONGO_STR"))
db = client["telegram_db"]
collection = db["lax_itsm"]

# Signed URL Generator
def generate_signed_url(key):
    s3 = boto3.client(
        "s3",
        region_name=os.getenv("SPACES_REGION"),
        endpoint_url=os.getenv("SPACES_ENDPOINT"),
        aws_access_key_id=os.getenv("SPACES_KEY"),
        aws_secret_access_key=os.getenv("SPACES_SECRET"),
    )
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': os.getenv("SPACES_BUCKET"),
            'Key': key
        },
        ExpiresIn=300  # 5 minutes
    )
    return url

@app.route("/")
def list_images():
    messages = list(collection.find().sort("timestamp", -1))
    for msg in messages:
        if "image_url" in msg:
            key = msg["image_url"].split("/")[-1]
            msg["signed_url"] = generate_signed_url(key)
    return render_template("list.html", messages=messages)

@app.route("/detail/<id>")
def detail_image(id):
    message = collection.find_one({"_id": ObjectId(id)})
    if "image_url" in message:
        key = message["image_url"].split("/")[-1]
        message["signed_url"] = generate_signed_url(key)
    return render_template("detail.html", message=message)

if __name__ == "__main__":
    app.run(debug=True)
