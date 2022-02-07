import os
import tensorflow.compat.v1 as tf
import person_detector
from config import NEG_FOLDER, POS_FOLDER

command = """
python retrain.py --bottleneck_dir=tf/training_data/bottlenecks --model_dir=tf/training_data/inception --summaries_dir=tf/training_data/summaries/basic --output_graph=tf/training_output/retrained_graph.pb --output_labels=tf/training_output/retrained_labels.txt --image_dir=./images/classified --how_many_training_steps=50000 --testing_percentage=20 --learning_rate=0.001
"""


if __name__ == "__main__":
    detection_graph = person_detector.open_graph()

    positive_images = [f for f in os.listdir(POS_FOLDER) if os.path.isfile(os.path.join(POS_FOLDER, f))]
    negative_images = [f for f in os.listdir(NEG_FOLDER) if os.path.isfile(os.path.join(NEG_FOLDER, f))]

    with detection_graph.as_default():
        with tf.Session() as sess:
            for pos in positive_images:
                img_filename = f'{POS_FOLDER}/{pos}'
                img = person_detector.get_person(img_filename, sess)
                if not img:
                    continue
                img = img.convert('L')
                print(f"Found person on {img_filename}. Saving new image...")
                img.save(img_filename, "jpeg")
            
            for neg in negative_images:
                img_filename = f'{NEG_FOLDER}/{neg}'
                img = person_detector.get_person(img_filename, sess)
                if not img:
                    continue
                img = img.convert('L')
                print(f"Found person on {img_filename}. Saving new image...")
                img.save(img_filename, "jpeg")
