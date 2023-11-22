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
        "If none, just say nothing.\n"
        "Examples of (1): \n"
        "I want to see a list of schedule for today.\n"
        "What's my schedule on 12/24/2023?\n"
        "Examples of (2): \n"
        "Can you add a meeting with my ConvAI teammates this Friday at 4PM?. The location is Building 942 Room 308.\n"
        "I have a meeting with Selena Gomez tomorrow at 2PM. Please create a schedule.\n"
        "Examples of (3): \n"
        "I have a conference talk next Thursday. Can you plan what I should do to prepare for it?\n"
        "I have a computing 2 homework due on 11/30. Create a study schedule for me.\n"
        "Can you help me plan for a paper submission due 12/1?\n"
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
  "startTime": "2023-11-28T09:00:00-07:00",
  "endTime": "2023-11-28T17:00:00-07:00",
  "timeZone": "America/Los_Angeles",
  "attendeesEmail": ["ryangosling@example.com"]
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
      
      # reformat json
      message_json = json.loads(message)
      
      message_json['start'] = dict(dateTime=message_json['startTime'],
                                   timeZone=message_json['timeZone'])
      message_json['end'] = dict(dateTime=message_json['endTime'],
                                 timeZone=message_json['timeZone'])
      message_json['attendees'] = dict(emails=message_json['attendeesEmail'])
      
      del message_json['startTime']
      del message_json['endTime']
      del message_json['timeZone']
      del message_json['attendeesEmail']
      
      print(">>===========================================")
      print("Adding the event to the calendar...")
      event = self.service.events().insert(calendarId=self.calendarId, body=message_json).execute()
      
      return 'Event created: %s' % (event.get('htmlLink'))
    
    except:
      print("Error occurred! ")
      
      return None


  def _prompt_detect_date(self, text):
    user_prompt = ("""Do not respond yet. """
"""Detect any time-related phrase from the given input from the user and resolve it into a date in the format of YYYY/MM/DD and the date after that day YYYY/MM/DD+1day.
Examples include today, tomorrow, this Wednesday, next Tuesday, last Friday, 11/13, November 5th, 13th of July.
When the detected word is day of week, make sure to include adjective in front of it such as "this", "next", "upcoming", "last", "past".
\n\n
Your output must be in JSON format. {"detected_phrase": <detected phrase>, "date": <YYYY/MM/DD>, "date_after_date": <YYYY/MM/DD>}
\n\n
Example 1
Input: Today is 2023/1/2. ... I want to schedule a meeting at 5PM tomorrow.
Output: {"detected_phrase": "tomorrow", "date": "2023/1/3", "date_after_date": "2023/1/4"}

Example 2
Input: Today is 2023/1/2. ... What time does the class start next Friday?
Output: {"detected_phrase": "next Friday", "date": "2023/1/13", "date_after_date": "2023/1/14"}

Example 3
Input: Today is 2023/1/2. ... What is the date of this upcoming Friday?
Output: {"detected_phrase": "this upcoming Friday", "date": "2023/1/6", "date_after_date": "2023/1/7"}
"""
f"\n\nInput: Today is {datetime.datetime.today().date()}. ... {text}")
    self.messages.append({
        "role": "user",
        "content": user_prompt,
    })

    print(">>===========================================")
    print("[Prompt for detecting date-related expression]")
    print(user_prompt)
      
    # Call ChatGPT
    response = self.call()
    message = response.choices[0].message.content
    
    # some cleansing if needed
    if 'json' in message:
      message = re.findall(r"(?<=```json)[\S\s]*(?=```)", message)[0]
      message = message.strip()
      
    init_result = json.loads(message)
    
    date_expression = init_result['detected_phrase'] # detected_phrase
    date_min = init_result['date'] #date
    date_max = init_result['date_after_date'] #date+1
    
    print("[Detected date]")
    print(date_expression, date_min)
      
    return date_expression, date_min, date_max


  def _prompt_summarize_calendar(self, text):
    
    date_expression, date_min, date_max = self._prompt_detect_date(text)
    
    date_min = parser.parse(date_min)
    date_min = date_min.isoformat().split('+')[0] + "Z"
    date_max = parser.parse(date_max)
    date_max = date_max.isoformat().split('+')[0] + "Z"

    print(">>===========================================")
    print("Sending request to Google Calendar API...")
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
    output_string +="You have total {0} schedules for {1}, {2}.\n".format(len(message_dict['schedule']), date_expression, date_min[:10])
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
    
    formatted_string = self.analysis_dialogue_gpt_call(text)
    
    message_json = self.create_schedule_dialogue_gpt_call(formatted_string)
    
    # some cleansing if needed
    message_json = message_json["Tasks"]
    
    # reformat json
    reformat_message_json = []
    for old_json in message_json:
      new_json = {}
      new_json['summary'] = old_json['Task']
      new_json['start'] = dict(dateTime=old_json['Start Time'],
                               timeZone=old_json['timeZone'])
      new_json['end'] = dict(dateTime=old_json['End Time'],
                             timeZone=old_json['timeZone'])
      reformat_message_json.append(new_json)

    print(">>===========================================")
    print("Adding events to the calender...")
    for i, schedule in enumerate(reformat_message_json):
      print(f"{i}th event done")
      event = self.service.events().insert(calendarId=self.calendarId, body=schedule).execute()
      message_json[i]['URL'] = event.get('htmlLink')
      
    return "I made a plan as following and added them to your schedule\n\n" + json.dumps(message_json, indent=4)

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

    
  def analysis_dialogue_gpt_call(self, user_text):
    input_text = f"""###Instruction: The assistant is an expert in analyzing conversations for schedule management. It takes the user's conversation as input and analyzes what tasks need to be done, by when, and how many detailed tasks the user desires. The assistant recognizes the user's conversation and performs accurate analysis.
  Output Goals:
  Target Task, Target Time, Maximum Number of Detailed Tasks

  Considerations:

  1. If the target task and target time are not clear in your analysis of the user's conversation, you must output a response stating, "Please suggest a target task or target time."
  2. If the maximum number of detailed tasks is not clear in your analysis of the user's conversation, set that number to 3.

  Please refer to the following examples for your response
  Example 1:
  Input: I need to complete a C++ programming assignment on matrix multiplication optimization within 3 days from today. Please divide it into 4 tasks for scheduling.
  Output(JSON type):
  "Target Task": "Completing a C++ programming assignment on matrix multiplication optimization",
  "Target Time": "3 days from today",
  "Maximum number of detailed tasks": "four"

  Example 2:
  Input: I need to select a paper on multi-task learning, familiarize myself with it, and then present it by next Monday.
  Output(JSON type):
  "Target Task": "Research and presentation on a multi-task learning paper",
  "Target Time": "Next Monday",
  "Maximum number of detailed tasks": "three"

  Example 3:
  Input: I need to coordinate our team's business trip schedule with another team and submit a report on the travel plan by next Wednesday. Please suggest a schedule divided into 5 detailed tasks.
  Output(JSON type):
  "Target Task": "Coordinating our team's business trip schedule with another team and writing a report on the travel plan",
  "Target Time": "Next Wednesday",
  "Maximum number of detailed tasks": "five"

  ###User Input:
  """
    input_text += user_text
    print(">>===========================================")
    print("[Prompt for extracting information from user request.]")
    print(input_text)

    self.messages.append({
        "role": "user",
        "content": input_text,
    })

    response = self.call()
    message = response.choices[0].message.content
      
    # some cleansing if needed
    if 'json' in message:
      message = re.findall(r"(?<=```json)[\S\s]*(?=```)", message)[0]
      message = message.strip()
    init_result = json.loads(message)
    init_result = {key.lower(): value for key, value in init_result.items()}

    formatted_string = f"Target Task: {init_result['target task']},\nTarget Time: {init_result['target time']},\nMaximum number of detailed tasks: {init_result['maximum number of detailed tasks']}"

    print("[Extracted information from the user request.]")
    print(formatted_string)

    return formatted_string

  def create_schedule_dialogue_gpt_call(self, formatted_string):
    input_text = """###Instruction : Please assist in optimized schedule management. As a 'Schedule Management Application', you act to suggest necessary tasks for work input by users, manage time effectively, and aid in overall productivity enhancement. The 'Schedule Management Application' performs the following roles for the "Target Task" and "Target Time" input by the user:

Create the required subtasks for the 'Target Task'. Distribute the required subtasks for the 'Target Task' appropriately by 'Target Time'. Finally, the assistant outputs the distribution of detailed tasks by 'Target Time' in JSON format.

Restrictions: 
1. Between 00:00:00 and 09:00:00 in Asia/Seoul time is sleep time and is excluded from schedule distribution. 
2. Asia/Seoul time between 12:00:00 and 13:00:00 is lunch time and is excluded from the schedule distribution. 
3. The period between 18:00:00 and 20:00:00 in Asia/Seoul time is dinner time and is excluded from the schedule distribution.
4. Assistant only outputs JSON.
5. You must strictly follow the json format presented in the example.
6. Create as many detailed tasks as the suggested Maximum number of detailed tasks.
Considerations: 
1. You must consider the entire duration of the given schedule and distribute tasks so that they are not concentrated on specific days. Be sure to not concentrate your work on a specific day or time. 
2. The time allotted for a single detailed tasks must be no more than 3 hours.

Here is an example
User Input:
Today is November 21, 2023.
Target Task: I need to select and present a paper on deep learning.
Target Time: Next Monday.
Maximum number of detailed task : five

Assistant Output(Should be JSON format):
{{
"Tasks": [
{{
  "Task": "Selecting a Paper",
  "Start Time": "2023-11-21T09:00:00",
  "End Time": "2023-11-21T12:00:00",
  "timeZone": 'Asia/Seoul'
}},
{{
  "Task": "Thoroughly Reading the Paper",
  "Start Time": "2023-11-21T13:00:00",
  "End Time": "2023-11-22T17:00:00",
  "timeZone": 'Asia/Seoul'
}},
{{
  "Task": "Researching Background Information",
  "Start Time": "2023-11-23T09:00:00",
  "End Time": "2023-11-23T12:00:00",
  "timeZone": 'Asia/Seoul'
}},
{{
  "Task": "Creating the Presentation",
  "Start Time": "2023-11-23T13:00:00",
  "End Time": "2023-11-24T17:00:00",
  "timeZone": 'Asia/Seoul'
}},
{{
  "Task": "Rehearsing the Presentation",
  "Start Time": "2023-11-25T09:00:00",
  "End Time": "2023-11-26T17:00:00",
  "timeZone": 'Asia/Seoul'
}}
]
}}

###User Input:
"""
    
    current_date = datetime.datetime.now()
    formatted_date = current_date.strftime("Today is %B %d, %Y.")
    
    input_text = input_text + formatted_date + "\n" + formatted_string

    print(">>===========================================")
    print("[Prompt for creating a plan according to user request.]")
    print(input_text)
    
    self.messages.append({
        "role": "user",
        "content": input_text,
    })
    
    # Call ChatGPT
    response = self.call()
    message = response.choices[0].message.content
    
    # some cleansing if needed
    if 'json' in message:
      message = re.findall(r"(?<=```json)[\S\s]*(?=```)", message)[0]
      message = message.strip()
    init_result = json.loads(message)

    return init_result



# Run an interactive console to chat with ChatGPT
def run_console(chatgpt):
    while True:
        # Receive user input
        prompt = input("👩🏻‍🦰 User: ")

        # Exit the loop if the user entered "exit"
        if prompt == "exit":
            break

        # Receive and display ChatGPT response
        response = chatgpt.prompt(prompt)
        print("🤖 ChatGPT:", response)
    print("The chat has ended")
    
    
    
