# IEOR 4950 Agentic AI for Data Science - Fall 2026
# Project 1: A Tool-Calling Agent 

## Agent Description
This is a Formula 1 Analyst Chatbot that helps fans of Formula 1 quickly catch up on the latest news, understand current/past championship standings, and explore their favourite driver's performance. It retrieves data from Motorsport RSS and Jolpica F1 API to answer fan's questions. 

The target users are busy fans who wants to quickly catch up after missing races, new F1 fans who need explanations on driver/team standings and championship scenarios, or avid fans who wish to explore their favourite driver/team's title prospect and historical performance. 

## How to get started?
Click on any of the sample queries dispalyed on the page to get started or ask it questions related to latest news related to a specific team/driver, current/past F1 championship standings, a team/driver's chances of winning championship, or a driver's best performing circuit. 

### Sample Queries 
1. Click on "Catch me up on the latest F1 news" to trigger query ->
"Catch me up on the most important Formula 1 news from the past week."

Expected Results: 
By default, return 5 of the latest headlines related to Formula 1. 

2. Click on "Can Norris still win the championship?" to trigger query ->
"Can Lando Norris still win the Drivers' Championship? Show me the path to championship title."

Expected Results: Response should include driver's current standing and gap to championship. It should also describe the driver's potential path to win the championship. 

3. Click on "Where does Hamilton perform the best?" to trigger query -> 
"Which circuits have historically been Lewis Hamilton's strongest?"

Expected Results: Response should include the driver's top 5 strongest circuits, including their average statistics at each circuit. 

Other Sample Queries:
- "How has Antonelli's performance been recently?"
- "What happened in the most recent race?"

## Tools Used 
Have at least three tools. 
At least one tool must make a request for external data such as an API or database.
### Tool 1: get_f1_news
Gets the latest relevant Formula 1 articles from Motorsport.com's public RSS feed. Articles can be related to a driver, team, or topic related to Formula 1. It will return 1 to 10 articles, by default 5 articles, from the public RSS feed. 

### Tool 2: get_championship_standings
Gets the current or selected-season Drivers' or Constructors' Championship standing from Jolpica F1 API. 


### Tool 3: analyze_title_potential
Gets relevant team or driver's race data from Jolpica F1 API, then analzes whether a team or driver remains in the running for the championship, showing the scenario needed to achieve the championship win. 


### Tool 4: analyze_driver_track_history
Gets relevant driver's historical race data from Jolpica API, then ranks a driver's strongest circuits based on past performance, specifcally using past wins, podiums, points, and average finishes. Returns 1 to 10 strongest circuit. 