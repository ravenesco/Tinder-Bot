# Tinder-Bot

## What is it about?

This Tinder bot will learn your interests and automate Tinder swiping game using its API and Tensorflow.

## Requirements

- Python v3.10.1
- Tensorflow v2.8.0rc1
- All required python packages with versions are listed in requirements.txt. Simply run `pip install -r requirements.txt` to install all of them at once
- Optional (to utilize GPU acceleration):
  - CUDA-compatible NVidia GPU (Developed and tested on GeForce RTX 2080 Super Max-Q)
  - CUDA v11.2
  - CUDNN v8.2.1

## How to use it?

### Tinder Auth Token

First and foremost you'll need to acquire a Tinder token that will authenticate your account. To do so, in a browser open Developer tools (F12 in Firefox).
Then, in the tab with Dev Tools go to https://tinder.com/app/recs. In Dev Tools, under the Network tab, search for a GET request to api.gotinder.com.
In Headers, it should contain **X-Auth-Token** that looks something like 943e7695-c8eb-415a-524d-67783caafc65.
Copy this token and paste it in config.py as **TINDER_TOKEN** value.

### To run Tinder game with a given trained model

Just run `py bot.py`.
For as long as you don't run out of the Likes limit on Tinder, it will be pulling more profiles filtered by preferences in your Tinder profile settings.
Each profile's photos will be evaluated based on the given model to calculate the profile's score. If the score passes the set threshold, Bot will like the profile.
Otherwise, it will pass it and go to the next profile. As of now, Tinder does not provide a strict Dislike function, all passed profiles will return to the pool of
profiles from which they will be pulled again later.

### To train model on your own preferences

1. Put a large number of images into the `.images/unclassified` folder.
2. Run `py image_classifier.py` which will pull those images one by one and let you mark them as **positive** (right arrow) or **negative** (left arrow).
*Bottom arrow will completely remove the image.* It will sort them into `./images/classified/positive` and `./images/classified/negative` folders.  
**Note:** new window with images might require you to manually select it and press Tab a couple of times for the *Next image* button to get in focus for arrow keys to work
properly.
3. Then run `py prepare_data.py` which will try and find a person on classified images, and grayscale the image for the model to work with. 
4. After all images are classified and processed by those two scripts, run 
`py retrain.py --bottleneck_dir=tf/training_data/bottlenecks --model_dir=tf/training_data/inception --summaries_dir=tf/training_data/summaries/basic --output_graph=tf/training_output/retrained_graph.pb --output_labels=tf/training_output/retrained_labels.txt --image_dir=./images/classified --how_many_training_steps=50000 --testing_percentage=20 --learning_rate=0.001`
**Note:** parameters like `--how_many_training_steps=50000 --testing_percentage=20 --learning_rate=0.001` might need to be adjsuted depending on your experience 
with precision results.
