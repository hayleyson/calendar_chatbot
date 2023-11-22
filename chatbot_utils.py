import calendar_utils
import json
import os
import ast
import re
import datetime
import openai
from openai import OpenAI
import dateutil.parser as parser

from ast import literal_eval


class CalendarChatGPT:
  def __init__(self, 
               openai_api_key, 
               model ="gpt-4-1106-preview", 
               json_output=False, 
               max_tokens=100,
               calendarId="primary",
               timezone="Korean Standard Time"):
    
    openai.api_key = openai_api_key
    self.max_tokens = max_tokens
    self.messages = []
    self.calendarId = calendarId
    self.timezone = timezone
    
    self.json_output = json_output
    
    self.client = OpenAI()
    self.model = model
    self.service = calendar_utils.get_calendar_service()

  def call(self):
    if self.json_output:
      response = self.client.chat.completions.create(
        model=self.model,
        response_format={ "type": "json_object" }, 
        messages=self.messages,
        max_tokens=self.max_tokens
      )
    else:
      response = self.client.chat.completions.create(
        model=self.model,
        messages=self.messages,
        max_tokens=self.max_tokens
      )
    return response
  
  def _prompt_intent(self, text):
    
    # Call ChatGPT for intent classification
    user_prompt = (
        f"{text}\n\nDo not respond yet. Classify user intention as one of 1, 2, 3. The meaning of the indices are as follows."
        "(1) Summarize events in the calendar. (2) Add an event to the calender. (3) Plan tasks and add multiple events to the calendar."
        "If none, just say nothing."
        "Example of (1): I want to see a list of schedule from Monday two weeks later."
    )
    
    print(">>===========================================")
    print("[Prompt for Intent Classification]")
    print(user_prompt + "\n")

    # Update the messages
    self.messages.append({
        "role": "user",
        "content": user_prompt,
    })

    # Call ChatGPT
    response = self.call()
    
    # Remove the last message
    self.messages.pop()

    return response
  
  def _prompt_detect_date(self, text):
    user_prompt = (f"""Do not respond yet. Today is {datetime.datetime.today().date()}."""
"""Detect any time-related phrase from the given input from the user and resolve it into a date in the format of YYYY/MM/DD and the date after that day YYYY/MM/DD+1day.
Examples include today, tomorrow, this Wednesday, next Tuesday, last Friday, 11/13, November 5th, 13th of July.
When the detected word is day of week, make sure to include adjective in front of it such as "this", "next", "upcoming", "last", "past".
\n\n
Your output must be in JSON format. {"detected_phrase": <detected phrase>, "date": <YYYY/MM/DD>, "date_after_date": <YYYY/MM/DD>}

\n\n
Example 1
Input: Today is 2023/1/2. ... I want to schedule a meeting at 5PM tomorrow.
Output: tomorrow, 2023/1/3, 2023/1/4

Example 2
Input: Today is 2023/1/2. ... What time does the class start next Friday?
Output: next Friday, 2023/1/13, 2023/1/14

Example 3
Input: Today is 2023/1/2. ... What is the date of this upcoming Friday?
Output: this upcoming Friday, 2023/1/6, 2023/1/7
\n\nInput: {text}
""")
    self.messages.append({
        "role": "user",
        "content": user_prompt,
    })

    # Call ChatGPT
    response = self.call()
    message = response.choices[0].message.content
    
    # some cleansing if needed
    if 'json' in message:
      message = re.findall(r"(?<=```json)[\S\s]*(?=```)", message)[0]
      message = message.strip()
      
    print(message)
    init_result = json.loads(message)
    
    date_expression = init_result['detected_phrase'] # detected_phrase
    date_min = init_result['date'] #date
    date_max = init_result['date_after_date'] #date+1
    
    return date_expression, date_min, date_max

  
  def _prompt_add_calendar(self, text):
    # Call ChatGPT for intent classification
    user_prompt = (
        f"{text}\n\nDo not respond yet."
        """You are a sophisticated calendar management assistant, 
adept at organizing and managing calendar schedules for both simple and complex tasks. 
Your role involves integrating tasks into a user's calendar with precision and 
ensuring that all details are accurately reflected.

For a task like "add meeting with Ryan Gosling tomorrow at 9 PM," 
Output a json that can be used as a calendar create request. 
Follow the below format. Only return the json.

Example
Input: "Today is 2023/11/22. Add an event about dance in the moon light at LaLa Land with Ryan Gosling (ryangosling@example.com). 
It will take place next Tuesday from 9 am to 5 pm LA times." 
Output:
{
  "summary": "Dancing in the moonlight",
  "location": "LaLa Land",
  "description": "I plan to dance with Ryan Gosling in the yellow dress.",
  "start": {
    "dateTime": "2023-11-28T09:00:00-07:00",
    "timeZone": "America/Los_Angeles",
  },
  "end": {
    "dateTime": "2023-11-28T17:00:00-07:00",
    "timeZone": "America/Los_Angeles",
  },
  "attendees": [
    {"email": "ryangosling@example.com"}
  ]
}

Input: "Today is 2023/11/22. Add an event about dance in the moon light at LaLa Land with Ryan Gosling (ryangosling@example.com). 
It will take place next Tuesday from 9 am to 5 pm LA times." 
Output:
{
  "summary": "Dancing in the moonlight",
  "location": "LaLa Land",
  "description": "I plan to dance with Ryan Gosling in the yellow dress.",
  "start": {
    "dateTime": "2023-11-28T09:00:00-07:00",
    "timeZone": "America/Los_Angeles",
  },
  "end": {
    "dateTime": "2023-11-28T17:00:00-07:00",
    "timeZone": "America/Los_Angeles",
  },
  "attendees": [
    {"email": "ryangosling@example.com"}
  ]
}
"""
f"\nThe timezone is {self.timezone}"""
f"\nToday is {datetime.datetime.today().date()}"
    )
    
    print(">>===========================================")
    print("[Prompt for Adding Calendar]")
    print(user_prompt + "\n")

    # Update the messages
    self.messages.append({
        "role": "user",
        "content": user_prompt,
    })

    # Call ChatGPT
    response = self.call()
    
    try:
      message = response.choices[0].message.content
      
      # some cleansing if needed
      if 'json' in message:
        message = re.findall(r"(?<=```json)[\S\s]*(?=```)", message)[0]
        message = message.strip()
      
      print(f"message: {message}")
      event = self.service.events().insert(calendarId=self.calendarId, body=json.loads(message)).execute()
      
      return 'Event created: %s' % (event.get('htmlLink'))
    
    except:
      print("Error occurred! ")
      
      return None
    
  def _prompt_summarize_calendar(self, text):
    
    date_expression, date_min, date_max = self._prompt_detect_date(text)
    
    date_min = parser.parse(date_min)
    date_min = date_min.isoformat().split('+')[0] + "Z"
    date_max = parser.parse(date_max)
    date_max = date_max.isoformat().split('+')[0] + "Z"
    
    event_list = calendar_utils.get_event_list_recent(self.service, timeMin=date_min, timeMax=date_max)
    
    # only take the necessary keys in the fetched event info
    event_list_new = []
    keys_to_extract = ['summary', 'start', 'organizer', 'end', 'location', 'attendees', ]
    for event in event_list:
        event_dict = {}
        for k in keys_to_extract:
            try:
                if k == 'start' or k == 'end':
                    event_dict[k] = event[k]
                    print(event_dict[k])
                    event_dict[k]['dateTime'] = event_dict[k]['dateTime'].replace(event_dict[k]['dateTime'][:10], date_min)
                else:
                    event_dict[k] = event[k]
            except KeyError:
                event_dict[k] = ''
        event_list_new.append(event_dict)

    # prompt chatgpt to rephrase the schedule in natural language
    input_text = f''' You are a sophisticated calendar management assistant, adapt at organizing and managing calendar schedules for both simple and complex tasks.\

    For a given day, check the user's Calendar input which is given as list of python dictionaries and output the agenda for the day in markdown using relevant emojis as bullet points. \
    Your output must be in this format. Json("date": <YYYY/MM/DD>, "schedule": <schedule>, "start_time":<HH:MM>, "Location": <location>, "Participants":<participants>)
    Here's an example:\

    Example 1
    Input: The given date is 2023-11-21. Which schedule do I have on the given day?\
    Output: Schedule is Check-in at HyattRegency Seattle, Start time ⏰ is After 4:00 PM, Location is Hyatt Regency, Seattle, Participants are\
    Sheryl Soo(sheryl@zapier.com), Mike Knoop (Knoop@zapier.com) and Going to Tacoma airport, Start time ⏰ is After 7:00 PM, Location is Seattle Tacoma International Airport\

    Example 2
    Input: The given date is 2023-11-03. Which schedule do I have on the given day?\
    Output: Schedule is Watching soccer game, Start time ⏰ is After 1:00 AM

    Calendar input: {event_list_new}\
    \n\nInput: The given date is {date_min[:10]}. {text}
    \n\nOutput: \
    '''

    print(input_text)

    self.messages.append({
        "role": "user",
        "content": input_text,
    })

    # Call ChatGPT
    response = self.call()
    message = response.choices[0].message.content
    
    # Post-processing JSON file
    message_dict = message.replace(' ', '')
    message_dict = message_dict.replace("true", "'true'")
    
    if 'json' in message_dict:
      message_dict = re.findall(r"(?<=```json)[\S\s]*(?=```)", message_dict)[0]
      message_dict = message_dict.strip()    
    
    message_dict = literal_eval(message_dict)

    output_string = ''
    output_string +="You have total {0} schedules for {1}, {2}.".format(len(message_dict['schedule']), date_expression, date_min[:10])
    for i in range(len(message_dict['schedule'])):
        output_string+= "schedule {0} is {1}. Start time ⏰ is {2}. ".format(i, message_dict['schedule'][i]['summary'], message_dict['schedule'][i]['start_time'])
        if message_dict['schedule'][i]['Location'] != '':
            output_string+="Location is {0}. ".format(message_dict['schedule'][i]['Location'])
        if message_dict['schedule'][i]['Participants'] != '' :
            output_string+="Participants are "
            for p in range(len(message_dict['schedule'][i]['Participants'])):
                if p == len(message_dict['schedule'][i]['Participants'])-1:
                    output_string+="and {0}. ".format(message_dict['schedule'][i]['Participants'][p]['email'])
                else:
                    output_string+="{0}, ".format(message_dict['schedule'][i]['Participants'][p]['email'])
                
        output_string+='\n'
        
    return output_string
  
  def _prompt_plan_and_add_calendar(self, text):
    
    user_prompt = (
    """
    ###Instruction : Please assist in optimized schedule management. As a 'Schedule Management Application', you act to suggest necessary tasks for work input by users, manage time effectively, and aid in overall productivity enhancement. The 'Schedule Management Application' performs the following roles for the "Target Task" and "Target Time" input by the user:

    Create the required subtasks for the 'Target Task'. Distribute the required subtasks for the 'Target Task' appropriately by 'Target Time'. Finally, the assistant outputs the distribution of detailed tasks by 'Target Time' in JSON format.

    Restrictions: 
    1. Between 00:00:00 and 09:00:00 in Asia/Seoul time is sleep time and is excluded from schedule distribution. 
    2. Asia/Seoul time between 12:00:00 and 13:00:00 is lunch time and is excluded from the schedule distribution. 
    3. The period between 18:00:00 and 20:00:00 in Asia/Seoul time is dinner time and is excluded from the schedule distribution.
    4. Assistant only outputs JSON.\n"""
    f"5. The timezone is {self.timezone}\n"
    f"6. Today is {datetime.datetime.today().date()}"
    """
    Considerations: 
    1. You must consider the entire duration of the given schedule and distribute tasks so that they are not concentrated on specific days. Be sure to not concentrate your work on a specific day or time. 
    2. The time allotted for a single detailed tasks must be no more than 3 hours.

    Here is an example
    User Input:
    Today is November 21, 2023.
    Target Task: I need to select and present a paper on deep learning.
    Target Time: Next Monday.
    Maximum number of detailed task : 5

    Assistant Output(Should be JSON format):
    {{
      "summery": "Selecting a Paper",
      "start": {{
      'dateTime': "2023-11-21T09:00:00+09:00",
      "timeZone": 'Asia/Seoul'
      }}
      ,
      "end": {{
      'dateTime': "2023-11-21T12:00:00+09:00",
      "timeZone": 'Asia/Seoul'
      }}
    }},
    {{
      "summary": "Thoroughly Reading the Paper",
      "start": {{
        "dateTime": "2023-11-21T13:00:00+09:00",
        "timeZone": "Asia/Seoul"
      }},
      "end": {{
        "dateTime": "2023-11-22T17:00:00+09:00",
        "timeZone": "Asia/Seoul"
      }}
    }},
    {{
      "summary": "Researching Background Information",
      "start": {{
        "dateTime": "2023-11-23T09:00:00+09:00",
        "timeZone": "Asia/Seoul"
      }},
      "end": {{
        "dateTime": "2023-11-23T12:00:00+09:00",
        "timeZone": "Asia/Seoul"
      }}
    }},
    {{
      "summary": "Creating the Presentation",
      "start": {{
        "dateTime": "2023-11-23T13:00:00+09:00",
        "timeZone": "Asia/Seoul"
      }},
      "end": {{
        "dateTime": "2023-11-24T17:00:00+09:00",
        "timeZone": "Asia/Seoul"
      }}
    }},
    {{
      "summary": "Rehearsing the Presentation",
      "start": {{
        "dateTime": "2023-11-25T09:00:00+09:00",
        "timeZone": "Asia/Seoul"
      }},
      "end": {{
        "dateTime": "2023-11-26T17:00:00+09:00",
        "timeZone": "Asia/Seoul"
      }}
    }}

    ###User Input:"""
    f"{text}")
    
    print(">>===========================================")
    print("[Prompt for Planning]")
    print(user_prompt + "\n")
    self.messages.append({
      "role": "user",
      "content": user_prompt,
      })

    # Call ChatGPT
    response = self.call()
    message = response.choices[0].message.content
    print(message)
    
    # some cleansing if needed
    if 'json' in message:
      message = re.findall(r"(?<=```json)[\S\s]*(?=```)", message)[0]
      message = message.strip()
      
    message_json = ast.literal_eval(message)
    
    for i, schedule in enumerate(message_json):
      event = self.service.events().insert(calendarId=self.calendarId, body=schedule).execute()
      message_json[i]['URL'] = event.get('htmlLink')
      
    return json.dumps(message_json)

  def prompt(self, text) -> str:
    
    # First prompt chatgpt for intent
    response = self._prompt_intent(text)
    # Parse the ChatGPT response to obtain intent
    message_content = response.choices[0].message.content
    print(f"message_content: {message_content}")
    
    if '1' in message_content:
      return self._prompt_summarize_calendar(text)
    
    elif '2' in message_content:
      return self._prompt_add_calendar(text)
    
    elif '3' in message_content:
      ## user input이 원하는 양식이게끔 어떻게 강제하지??
      return self._prompt_plan_and_add_calendar(text)
    
    else:
      ## ??
      self.messages.append({
        "role": "user",
        "content": text,
      })

      # Call ChatGPT
      response = self.call()

      # Save the returned message
      message = response.choices[0].message
      self.messages.append(message) ## ??
      
    ### add some default message instead of calling chatgpt.
    #   message = ("""Could you rephrase your request so that I can better understand your intent? I can assist you with the following."""
    #              "(1) Summarize events in the calendar. (2) Add an event to the calender. (3) Plan tasks and add multiple events to the calendar.")
      return message.content
