# Chatbot Le Point

## Name
Assistant Hôpitaux

## Description
The hospital ranking assistant allows interaction with Le Point's hospital rankings and exploration of its content. It enables users to ask questions to query one of the rankings and continue the conversation based on the results of the initial question. It is currently accessible through a simple Streamlit application, serving as a user interface for this initial POC phase.


## Installation
If you want to launch the Streamlit app, you should create a python environnement named 'chatbot_env_2' with the package from the "requirement.txt" file. 
You should as well get an API Key from Open AI and paste it in the '.env' file  to use our model: "gpt-4o-mini".
You get get it at:
https://platform.openai.com/docs/overview

## Usage
Here are the commands to launch the Streamlit app from the terminal anaconda for example: 
- input "conda activate chatbot_env_2"
Copy the path of the Front folder
- input "cd 'paste the path here'"
- input "streamlit run app.py"

Then you could ask your question.

## Code organization
The folder contains a file for the Streamlit frontend that sets up the entire visual aspect, including sanity checks, conversation history management to send multiple messages in a row, and the logic for selecting the pathology when multiple options might be applicable.

The code for the backend is structured into 4 classes:
A class Appels_LLM used for all LLM calls: sanity checks, information extraction, and conversational aspects.
A class Processing_class that manages the processing of information retrieved from the question and the exploitation of rankings.
A class Pipeline_class that orchestrates the entire flow and functions of the other classes to take a user question and provide the final answer.



## Support
You can contact Alexis CALVEZ from the company Eulidia at the following email address: acalvez@eulidia.com .



