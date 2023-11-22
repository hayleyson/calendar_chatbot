# Google Calendar-Grounded Chatbot
It is a GPT-4-based chatbot prototype that interacts with Google Calendar.

## More about Chatbot
- Link to be attached.

## Setup
0. This repository was developed using python 3.12
1. Preferably create a virtual environment and install dependencies. `pip install -r requirements.txt`
2. Create `.env` file in the project directory and paste the below info.
```
OPENAI_API_KEY=<your-openai-api-key>
```
3. Request `credentials.json` from the repository owner and place it in the project directory.
4. Ask the repository owner to add your email to test user list.  
For the last two steps, you can otherwise follow "Set up your environment" section in the Python Quickstart for using Google Calendar API document (See References) to set up your own Google Cloud project.

## Run
- open `demo.ipynb` and run cells.

## Teammates
- Kiseung Kim (kkskp@snu.ac.kr)
- Hye Ryung Son (hyeryung.son@snu.ac.kr)
- Jong Song (hyeongoon11@snu.ac.kr)
- Jeongseok Oh (luke0112@snu.ac.kr)

## Notes
- Developed as a mini-project of Conversational NLP course @ Seoul National University.

## Useful references
- [Python quickstart for using Google Calendar API](https://developers.google.com/calendar/api/quickstart/python)
- [Calendar API - events](https://developers.google.com/resources/api-libraries/documentation/calendar/v3/python/latest/calendar_v3.events.html)
