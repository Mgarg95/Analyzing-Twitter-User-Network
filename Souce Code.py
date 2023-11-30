
# Mapping my Twitter Network      				   
# Name : MANHA GARG                                       
# Source : Chapter 9 - Twitter Cookbook.py                         
                                                             


#all import statements needed
import twitter
import matplotlib.pyplot as plot
import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine
import json
import twitter
import networkx as netx
from functools import partial
from sys import maxsize as maxint


##Developer authorization - function to authorize the twitter login using OAuth
def oauth_twitter_login():

    # XXX: Go to http://twitter.com/apps/new to create an app and get values
    # for these credentials that you'll need to provide in place of these
    # empty string values that are defined as placeholders.
    # See https://developer.twitter.com/en/docs/basics/authentication/overview/oauth
    # for more information on Twitter's OAuth implementation.

    try: 

        CONSUMER_KEY = "eDsvZdho3RYDwX3nI8uX08xBV"
        CONSUMER_SECRET = "pDwfFgUCYYkc1aIXRl4VjRavujRIBHtv520qepcds3Bcj2d1gd"
        OAUTH_TOKEN = "905431918308495360-FPEpHy1l4RCYprb14A7SenQtaxP2WLQ"
        OAUTH_TOKEN_SECRET = "ZyknpZj0q3MiUuTvQchi1rWb8bJ1kDNaaMr6aOeybo8EG"

    
        auth_request = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                               CONSUMER_KEY, CONSUMER_SECRET)

        auth_response = twitter.Twitter(auth=auth_request)

        assert (auth_response != None) , "respone returned was null"

        print("Authorization successful!")
        print(auth_response)
        return auth_response
    except:

        print("unexpected error, twitter authorization failed")


#eoor handling_function sending the callable functions and its arguments as the argument and reference
def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw): 
    
    # A nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):
    
        if wait_period > 3600: # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise e
    
        # See https://developer.twitter.com/en/docs/basics/response-codes
        # for common codes
    
        if e.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429: 
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes...", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60*15 + 5)
                print('Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise e # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered {0} Error. Retrying in {1} seconds'.format(e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e
    # End of nested helper function
    
    wait_period = 2 
    error_count = 0 

    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError as e:
            error_count = 0 
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("URLError encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise
        except BadStatusLine as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("BadStatusLine encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise

#1_function to get friends and followers information of the given user
def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None), "Must have screen_name or user_id, but not both"
    
    # See http://bit.ly/2GcjKJP and http://bit.ly/2rFz90N for details
    # on API parameters
    
    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids, 
                              count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids, 
                                count=5000)

    friends_ids, followers_ids = [], []
    
    for twitter_api_func, limit, ids, label in [
                    [get_friends_ids, friends_limit, friends_ids, "friends"], 
                    [get_followers_ids, followers_limit, followers_ids, "followers"]
                ]:
        
        if limit == 0: continue
        
        cursor = -1
        while cursor != 0:
        
            # Use make_twitter_request via the partially bound callable...
            if screen_name: 
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else: # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']
        
            # XXX: You may want to store data during each iteration to provide an 
            # an additional layer of protection from exceptional circumstances
        
            if len(ids) >= limit or response is None:
                break

    # lists of friends and follower IDs of the user
    return friends_ids[:friends_limit], followers_ids[:followers_limit]

#2_function to get the user Profile information
def get_user_profile(twitter_api, screen_names=None, user_ids=None):
    # Must have either screen_name or user_id (logical xor)
    assert (screen_names != None) != (user_ids != None), "Must have screen_names or user_ids, but not both"

    items_to_info = {}

    items = screen_names or user_ids
    
    while len(items) > 0:
        # Process 100 items at a time per the API specifications for /users/lookup.
        # See http://bit.ly/2Gcjfzr for details.
        
        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]

        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup, 
                                            screen_name=items_str)
        else: # user_ids
            response = make_twitter_request(twitter_api.users.lookup, 
                                            user_id=items_str)
    
        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else: # user_ids
                items_to_info[user_info['id']] = user_info

    return items_to_info

#3_function to get most popular friends of the given user. i.e, top_count followers based on followers_count #****Own Code****#
def get_most_popular_friends(twitter_api, all_friends, top_count = None):
        top_friends = {}
        for friend in all_friends:
            friends_user_info = get_user_profile(twitter_api, user_ids = [friend])
            top_friends.update({friends_user_info[friend]["id"] : friends_user_info[friend]["followers_count"]})
        
        if(len(top_friends) >= top_count):
            min_value = sorted(top_friends.values(), reverse=True)[top_count-1]

        elif(len(top_friends) > 1):
            min_value = sorted(top_friends.values(), reverse=True)[len(top_friends)-1]

        else:
            min_value = 0

        top_friends = {key:value for key,value in top_friends.items() if value >= min_value} 

        return top_friends

#4_function to get friends and followers based on user id provided #****Own Code****#
def get_friends_and_followers_by_user_id(twitter_api, user_id, top_count = 5):
        friends_ids, followers_ids = get_friends_followers_ids(twitter_api,
                                                       user_id = user_id, 
                                                       friends_limit=50, 
                                                       followers_limit=50)
        return get_most_popular_friends(twitter_api, all_friends = set(friends_ids) & set(followers_ids), top_count = 5)


#5_function to crawl the top_n followers to get their top_n followers
def crawl_followers(twitter_api, screen_name, depth=2, all_followers = None):
    
    # Resolve the ID for screen_name and start working with IDs for consistency 
    # in storage
    assert (all_followers != None), "Dont have any follwers!"

    minimum_limit = 100
    unique_list = []
    user_info = make_twitter_request(twitter_api.users.show, screen_name=screen_name)
    #print(user_info)

    user_id = user_info['id']
    #print(user_id)
    followers_friends_dictionary = {} #a new dictionary
    followers_friends_list = [] #a new list
    result_queue = all_followers
    followers_friends_list.append(user_id)
    followers_friends_list.extend(list(result_queue.keys()))
    followers_friends_dictionary.update({user_id : list(result_queue)})

    #adding a node to the existing graph
    add_a_node(user_id)

    #adding from a list to the existing graph
    add_node(list(result_queue.keys()))
    for n in list(result_queue.keys()):
            add_a_edge((user_id,n))

    d = 1

    next_queue_list = list(result_queue.keys())
    #iterate till the minimum limit of nodes are gathered
    while len(followers_friends_list) < minimum_limit :
        print("Size of the graph is : ", len(followers_friends_list))
        d += 1 #****Own Code****#
        (queue, next_queue_list) = (list(set(next_queue_list)), [])
        for f_id in queue: 
            top_reciprocal_friends_followers = get_friends_and_followers_by_user_id(twitter_api, f_id)  
            unique_friends_followers = list(set(top_reciprocal_friends_followers) - set(followers_friends_list))
            followers_friends_list += unique_friends_followers
            #adding new nodes to graph
            add_node(unique_friends_followers)
            for n in top_reciprocal_friends_followers:
                add_a_edge((f_id,n))
            followers_friends_dictionary.update({f_id : unique_friends_followers})
            next_queue_list +=  unique_friends_followers
            if(len(followers_friends_dictionary) > minimum_limit):
                return followers_friends_dictionary
    return followers_friends_dictionary

#variable to define the social network graph
sn_graph = netx.Graph()

#6_function to add nodes from a list to the existing graph
def add_node(node_list):
    sn_graph.add_nodes_from(node_list)


#7_function to add a node to the existing graph
def add_a_node(node):
    sn_graph.add_node(node)


#8_function to add edges from a list to the existing graph
def add_edge(edge_list):
    sn_graph.add_edges_from(edge_list)


#9_function to add a edge to the existing graph
def add_a_edge(edge):
    sn_graph.add_edge(*edge)


#10_function to display the graph information on the console
def display_graph(): #****Own Code****#
    file = open("FinalOutputFile.txt","w") 

    file.write("\nSize of Network in terms of Nodes : " + str(sn_graph.number_of_nodes())) 
    print("Network size interms of nodes : ", sn_graph.number_of_nodes())

    file.write("\nSize of Network in terms of Edges : : " + str(sn_graph.number_of_edges()))
    print("Network size interms of edges : : ",sn_graph.number_of_edges())

    file.write("\nSize of Network in terms of Diameter : " + str(netx.diameter(sn_graph, e=None, usebounds=False)))
    print("Network size interms of Diameter : " , netx.diameter(sn_graph, e=None, usebounds=False))

    file.write("\nSize of Network in terms of Average distance : " +  str(netx.average_shortest_path_length(sn_graph, weight=None)))
    print("Network size interms of Average distance : " , netx.average_shortest_path_length(sn_graph, weight=None))

    file.close() 
    netx.draw(sn_graph, with_labels=True)
    plot.savefig('OutputGraphView.png', bbox_inches=0, orientation='landscape', pad_inches=0.5)
    plot.show()


#the main function #Self written code#
if __name__ == "__main__":
    try:
        print(".............................................................")
        print("\n Main code execution Started.....")
        print("Starting to authorize twitter login......")
        twitter_api_response = oauth_twitter_login()

        print(".............................................................")
        print("\n #1 requirement start ::")
        print("using my own twitter profile as the starting point")
        screen_name = "manha_garg" #1  twitter user -- starting point

        print(".............................................................")
        print("\n #2 requirement start ::")
        friends_ids_retrieved, followers_ids_retrieved = get_friends_followers_ids(twitter_api_response, 
                                                       screen_name=screen_name, 
                                                       friends_limit=50, 
                                                       followers_limit=50)
    
        print("\n fetched friends Ids list : ")
        
        print(friends_ids_retrieved)
        print("\n fetched followers Ids list : ")
        print(followers_ids_retrieved)

        print(".............................................................")
        print("\n #2 requirement start ::")
        print("Identifying the reciprocal friends")
        reciprocal_friends_list = set(friends_ids_retrieved) & set(followers_ids_retrieved)
        print("\n The list of reciprocal friends is as follows :")
        print(list(reciprocal_friends_list))

        print(".............................................................")
        print("\n #4 requirement start ::")
        print("Identifying the top 5 most popular friends")
        top_popular_friends = get_most_popular_friends(twitter_api = twitter_api_response, all_friends = reciprocal_friends_list , top_count = 5)
        print("Displaying Top 5 friends :: ")
        print(top_popular_friends)

        print(".............................................................")
        print("\n #5 requirement start ::")
        print("Identifying friends who are distance-1, distance-2 and so on....")
        crawl_followers(twitter_api = twitter_api_response, screen_name = screen_name, depth = 10, all_followers = top_popular_friends)
    
        print(".............................................................")
        print("\n #6 and 7 requirement start ::")
        print("Creating a social network based on the results from Req 5")
        print("\n ")
        display_graph()
    
    except twitter.api.TwitterHTTPError as e:
        print("Error occured while running the program. Please run again after sometime")