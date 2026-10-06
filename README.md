# IEOR 4950 Agentic AI for Data Science 
# Project 1: A Tool-Calling Agent 


## Agent Description
This is a Formula 1 Analyst Chatbot designed to keep fans of Formula 1 updated on the most recent news, XXX, and XXX. 

## How to get started?
Ask about XXX

### Sample Queries 
1. Click on "Catch me up on the latest F1 news" to trigger query -> "XXX"

Expected Results: 

2. Click on "Can Norris still win the championship?" to trigger query -> "XXX"

Expected Results:

3. Click on "Where does Hamilton perform the best?" to trigger query -> "XXX"

Expected Results: 


## Tools Used 
Have at least three tools. 
At least one tool must make a request for external data such as an API or database.
### Tool 1: get_f1_news
Gets the current relevant Formula 1 articles from Motorsport.com's public RSS feed. Articles can be related to a driver, team, or topic related to Formula 1. It will return 1 to 10 articles from the public RSS feed. 

{"type": "function", "function": {"name": "get_f1_news", "description": "Get current, source-linked Formula 1 headlines from Motorsport.com's public RSS feed. Use for current news; the feed does not support historical date-range searches.", "parameters": {"type": "object", "properties": {"subject": {"type": "string", "description": "A driver, team, or topic, for example 'McLaren'."}, "max_articles": {"type": "integer", "description": "Articles to return, 1 to 10. Defaults to 5."}}, "required": ["subject"]}}}


### Tool 2: get_championship_standings
Gets the current or selected-season Drivers' or Constructors' Championship standing from JoiAPI. 

{"type": "function", "function": {"name": "get_championship_standings", "description": "Get current or selected-season Drivers' or Constructors' Championship standings. Use for current points or rank.", "parameters": {"type": "object", "properties": {"championship": {"type": "string", "enum": ["drivers", "constructors"], "description": "The championship table."}, "season": {"type": "string", "description": "A season year such as '2026', or 'current'. Defaults to current."}}, "required": ["championship"]}}}


### Tool 3: analyze_title_potential
Gets relevant XXX from JoiXX API, then analzes whether a driver or team remains in the running for the championship, showing the scenario needed to achieve the championship win. 

{"type": "function", "function": {"name": "analyze_title_potential", "description": "Analyze whether a driver or constructor remains in the running for the championship and show a transparent catch-up scenario. Not a betting or probability forecast.", "parameters": {"type": "object", "properties": {"subject": {"type": "string", "description": "Driver/team name or id, such as 'norris' or 'McLaren'."}, "championship": {"type": "string", "enum": ["drivers", "constructors"], "description": "The title to analyze."}, "season": {"type": "string", "description": "A season year such as '2026', or 'current'. Defaults to current."}}, "required": ["subject", "championship"]}}}


### Tool 4: analyze_driver_track_history
Gets XXX from Jolpica API, then ranks a driver's strongest circuits based on past performance, specifcally using past wins, podiums, points, and average finishes. Returns 1 to 10 strongest circuit. 

{"type": "function", "function": {"name": "analyze_driver_track_history", "description": "Rank a driver's strongest historic F1 circuits using wins, podiums, points, and average finishes. Use for questions about track history or location strength.", "parameters": {"type": "object", "properties": {"driver": {"type": "string", "description": "Jolpica driver id, such as 'hamilton', 'verstappen', or 'norris'."}, "seasons_back": {"type": "integer", "description": "Recent seasons to analyze, 1 to 12. Defaults to 8."}, "limit": {"type": "integer", "description": "Circuits to return, 1 to 10. Defaults to 5."}}, "required": ["driver"]}}}


