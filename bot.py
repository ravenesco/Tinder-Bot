import datetime
from random import random
from time import sleep
import requests
import tensorflow.compat.v1 as tf
from geopy.geocoders import Nominatim
tf.disable_v2_behavior()
import json
import os
from time import time
from PIL import Image
import person_detector
from config import (JSON_LOGS_FOLDER, PROFILES_FILE, TINDER_GAME_LOGS_FOLDER,
                    TINDER_TOKEN, TINDER_URL, TMP_IMAGE_FOLDER,
                    UNCLASSIFIED_IMAGE_FOLDER, VERIFIED_ACC_MULTIPLIER)
from likeliness_classifier import Classifier

geolocator = Nominatim(user_agent="bot")


# Ensure all necessary folders and files are created
if not os.path.isdir(UNCLASSIFIED_IMAGE_FOLDER):
    os.makedirs(UNCLASSIFIED_IMAGE_FOLDER)

if not os.path.isdir(TMP_IMAGE_FOLDER):
    os.makedirs(TMP_IMAGE_FOLDER)

if not os.path.isdir(JSON_LOGS_FOLDER):
    os.makedirs(JSON_LOGS_FOLDER)

if not os.path.isdir(TINDER_GAME_LOGS_FOLDER):
    os.makedirs(TINDER_GAME_LOGS_FOLDER)

try:
    f = open(PROFILES_FILE, "r")
except IOError:
    f = open(PROFILES_FILE, "w")
finally:
    f.close()


def fix_gpu_memory_alloc():
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        try:
            # Currently, memory growth needs to be the same across GPUs
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            logical_gpus = tf.config.experimental.list_logical_devices('GPU')
            print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
        except RuntimeError as e:
            # Memory growth must be set before GPUs have been initialized
            print(e)


class Person(object):

    def __init__(self, data, instagram, api):
        self._api = api

        self.id = data["_id"]
        self.name = data.get("name", "Unknown")

        self.bio = data.get("bio", "")
        self.distance = data.get("distance_mi", 0) / 1.60934

        self.birth_date = datetime.datetime.strptime(data["birth_date"], '%Y-%m-%dT%H:%M:%S.%fZ') if data.get(
            "birth_date", False) else None
        self.gender = ["Male", "Female", "Unknown"][data.get("gender", 2)]

        self.images = list(map(lambda photo: photo["url"], data.get("photos", [])))

        self.jobs = list(
            map(lambda job: {"title": job.get("title", {}).get("name"), "company": job.get("company", {}).get("name")}, data.get("jobs", [])))
        self.schools = list(map(lambda school: school["name"], data.get("schools", [])))

        self.badges = list(map(lambda badge: badge["type"], data.get("badges", [])))
        self.profile_verified = True if 'selfie_verified' in self.badges else False

        self.instagram_linked = instagram

        self.recently_active = data['recently_active']

        if data.get("pos", False):
            self.location = geolocator.reverse(f'{data["pos"]["lat"]}, {data["pos"]["lon"]}')

    def __repr__(self):
        return f"{self.id}  -  {self.name} ({self.birth_date.strftime('%d.%m.%Y')})"

    def like(self):
        return self._api.like(self.id)

    def dislike(self):
        return self._api.dislike(self.id)

    def predict_likeliness(self, classifier, sess):
        try:
            ratings = []
            for image in self.images:
                req = requests.get(image, stream=True)
                tmp_filename = f"{TMP_IMAGE_FOLDER}/run.jpg"
                if req.status_code == 200:
                    with open(tmp_filename, "wb") as f:
                        f.write(req.content)
                img = person_detector.get_person(tmp_filename, sess)
                if img:
                    img = img.convert('L')
                    img.save(tmp_filename, "jpeg")
                    certainty = classifier.classify(tmp_filename)
                    pos = certainty["positive"]
                    ratings.append(pos)
            ratings.sort(reverse=True)
            ratings = ratings[:5]
            if len(ratings) == 0:
                return 0.001
            return ratings[0]*0.8 + sum(ratings[1:])/len(ratings[1:])*0.2
        except Exception:
            return 0.001
    
    def download_images(self, folder_img=UNCLASSIFIED_IMAGE_FOLDER, sleep_max_for=0):
        # Save photos a of a person into unclassified image folder if person's ID isn't on the list yet
        with open(PROFILES_FILE, "r+") as f:
            lines = f.readlines()
            if f'{self.id}\n' in lines:
                return
        with open(PROFILES_FILE, "a") as f:
            f.write(self.id + "\n")

        index = 0
        birthdate = 'None'
        try:
            birthdate = f'{self.birth_date.day}-{self.birth_date.month}-{self.birth_date.year}'
        except:
            None

        for image_url in self.images:
            response = requests.get(image_url, stream=True)
            if response.status_code == 200:
                pic = Image.open(response.raw)
                pic.save(f'{folder_img}/{self.id}_{self.name}_{birthdate}_{index}.jpg')
                index += 1

            sleep(random()*sleep_max_for)


class Profile(Person):
    def __init__(self, data, api):
        super().__init__(data["user"], api)

        self.email = data["account"].get("email")
        self.phone_number = data["account"].get("account_phone_number")

        self.age_min = data["user"]["age_filter_min"]
        self.age_max = data["user"]["age_filter_max"]

        self.max_distance = data["user"]["distance_filter"]
        self.gender_filter = ["Male", "Female"][data["user"]["gender_filter"]]


class tinderAPI():

    def __init__(self, token):
        self._token = token

    def profile(self):
        data = requests.get(TINDER_URL + "/v2/profile?include=account%2Cuser", headers={"X-Auth-Token": self._token}).json()
        return Profile(data["data"], self)

    def matches(self, limit=10):
        data = requests.get(TINDER_URL + f"/v2/matches?count={limit}", headers={"X-Auth-Token": self._token}).json()
        with open('matches1.json', 'w') as f:
            json.dump(data, f)
        return list(map(lambda match: Person(match["person"], self), data["data"]["matches"]))

    def like(self, user_id):
        data = requests.get(TINDER_URL + f"/like/{user_id}", headers={"X-Auth-Token": self._token}).json()
        return {
            "is_match": data["match"],
            "likes_remaining": data["likes_remaining"]
        }

    def dislike(self, user_id):
        requests.get(TINDER_URL + f"/pass/{user_id}", headers={"X-Auth-Token": self._token}).json()
        return True

    def nearby_people(self):
        # Request new people data and save it to it's log
        try:
            now = datetime.datetime.now()
            dt_string = str(now.strftime("%d-%m-%Y--%H-%M-%S"))
            json_filename = JSON_LOGS_FOLDER + "/" + dt_string + '.json'

            data = requests.get(TINDER_URL + "/v2/recs/core", headers={"X-Auth-Token": self._token, "platform": "web"}).json()

            if data["meta"]["status"] != 200:
                if data["meta"]["status"] == 429:
                    print(f"[-] [{dt_string}] Too many requests sent to Tinder API. Your account was suspended for some time. Come back later ^^")
                    print("Quitting...")
                    return [429]
                print(f"[-] [{dt_string}] Error receiving data from Tinder. Code: ", data["meta"]["status"])
                print(f"[-] [{dt_string}] Error message: ", data["error"]["message"])
                print("Skipping...")
                quit()

            with open(json_filename, "w") as f:
                json.dump(data, f)

            print('Saved new log: ' + json_filename)

            return list(map(lambda user: Person(user["user"], True if "instagram" in user else False, self), data["data"]["results"]))

        except Exception:
            sleep(random()*10)
            return


if __name__ == "__main__":
    # Prevents CUDNN_STATUS_ALLOC_FAILED error
    fix_gpu_memory_alloc()

    # Initiate API with Tinder token
    api = tinderAPI(TINDER_TOKEN)

    # Game log
    now = datetime.datetime.now()
    dt_string = str(now.strftime("%d-%m-%Y--%H-%M-%S"))
    auto_tinder_log_filename = TINDER_GAME_LOGS_FOLDER + "/" + dt_string + '.txt'

    detection_graph = person_detector.open_graph()

    # Daily Likes limit, var will be updated as response from Tinder on each Like
    likes_remaining = 100

    # Play until daily Likes limit is reached
    with detection_graph.as_default():
        with tf.Session() as sess:
            classifier = Classifier(graph="./tf/training_output/retrained_graph.pb",
                                    labels="./tf/training_output/retrained_labels.txt")

            while likes_remaining > 0:
                people = []
                try:
                    people = api.nearby_people()
                except:
                    pass

                # Exit script if the account is suspended for sending too many requests to Tinder API
                if people == [429]:
                    exit()

                for person in people:
                    try:
                        # Evaluation of person's photos
                        score = person.predict_likeliness(classifier, sess)

                        # Score multiplier for verified accounts and those with linked Instagram (sort of verification as well)
                        if person.profile_verified or person.instagram_linked:
                            score *= VERIFIED_ACC_MULTIPLIER

                        # Downlaod person's images
                        person.download_images(UNCLASSIFIED_IMAGE_FOLDER)

                        # Save log of the game
                        birthdate = 'None'
                        try:
                            birthdate = f'{person.birth_date.day}.{person.birth_date.month}.{person.birth_date.year}'
                        except:
                            None

                        with open(auto_tinder_log_filename, "a+", encoding="utf-8") as logs:
                            logs.write("-------------------------\n")
                            logs.write(f"ID: {person.id}\n")
                            logs.write(f"Name: {person.name}\n")
                            logs.write(f"Birthdate: {birthdate}\n")
                            logs.write(f"Bio: {person.bio}\n")
                            logs.write(f"Schools: {person.schools}\n")
                            logs.write(f"Images: {person.images}\n")
                            logs.write(f"Verified: {person.profile_verified}\n")
                            logs.write(f"Instagram linked: {person.instagram_linked}\n")
                            logs.write(f"Score: {score}\n")

                            print("-------------------------")
                            print(f"ID: {person.id}")
                            print(f"Name: {person.name}")
                            print(f"Birthdate: {birthdate}")
                            print(f"Bio: {person.bio}")
                            print(f"Schools: {person.schools}")
                            print(f"Images: {person.images}")
                            print(f"Verified: {person.profile_verified}")
                            print(f"Instagram linked: {person.instagram_linked}")
                            print(f"Score: {score}")

                            if score > 0.6:
                                res = person.like()
                                likes_remaining = int(res["likes_remaining"])
                                logs.write("LIKE\n")
                                logs.write(f"Response: {res}\n")
                                print("LIKE")
                                print(f"Response: {res}")
                                if likes_remaining == 0:
                                    break
                            else:
                                res = person.dislike()
                                logs.write("DISLIKE\n")
                                logs.write(f"Response: {res}\n" % res)
                                print("DISLIKE")
                                print(f"Response: {res}")
                    except:
                        pass
            print('Your Likes count is 0. Closing the session...')
    classifier.close()
