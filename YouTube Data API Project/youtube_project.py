from googleapiclient.discovery import build
import pandas as pd
import pymongo
import psycopg2        # install library
import streamlit as st
from PIL import Image 
from streamlit_option_menu import option_menu


# CREATING OPTION MENU
st.set_page_config(page_title= "Youtube Data Harvesting and Warehousing | By Thana Lakshmi",
                   page_icon= '📈',
                   layout='wide',
                   initial_sidebar_state="expanded",
                   menu_items={'About': """# This app is created by *Thana Lakshmi!*"""})
st.title(':block[WELCOME TO YOUTUBE CHANNEL DATA HARVESTING AND WAREHOUSING....]:rocket:')
icon=Image.open("youtube_logo.png")
st.image(icon)

with st.sidebar:
    selected = option_menu(None, ["Home","Extract & Transform","View"],
                           icons=["house-fill",'youtube','bar-chart-fill',],
                           default_index=0,
                           orientation="vertical",
                           styles={"nav-link": {"font-size": "30px", "text-align": "centre", "margin": "0px",
                                                "--hover-color": "#C80101"},
                                   "icon": {"font-size": "30px"},
                                   "container" : {"max-width": "6000px"},
                                   "nav-link-selected": {"background-color": "#C80101"}})
  

# MongoDB connect      
client=pymongo.MongoClient('mongodb+srv://thanalakshmi:thanam@cluster0.5jj0you.mongodb.net/?retryWrites=true&w=majority')
db=client['youtube_v3']
col=db['channels']

# PostpreSQL connect 
cont=psycopg2.connect(host='localhost',user='postgres',password='thanalakshmi',port=5432,database='kavi') # connect to postgresql
cor=cont.cursor()

#API connect fun
def API_connect():
    api_key='AIzaSyB25u2aQ97ptdxn07i6O_iH4B9tNgVgNi0'
    #channel_id=['UCF_ENoqUf6yYVzMYSIY8JpA']
    youtube=build('youtube','v3',developerKey=api_key)
    return youtube

#channel_details
def get_channel_stats(channel_id):
  request=API_connect().channels().list(part='snippet,contentDetails,statistics',
                                  id=channel_id)

  data=[]
  response=request.execute()
  data.append(dict(channel_name=response['items'][0]['snippet']['title'],
            channel_id=response['items'][0]['id'],
            subscribers_count=int(response['items'][0]['statistics']['subscriberCount']),
            channel_views_count=int(response['items'][0]['statistics']['viewCount']),
            channel_videos_count=int(response['items'][0]['statistics']['videoCount']),
            channel_description=response['items'][0]['snippet']['description'],
            playlist_id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']))

  return data

#playlist_details fun
def get_playlist(channel_id):
  request=API_connect().channels().list(part='snippet,statistics,contentDetails',
                                  id=channel_id)
  data=[]
  response=request.execute()
  for item in response['items']:
        data.append({"playlist_id":item['contentDetails']['relatedPlaylists']['uploads'],
             "Channel_id":channel_id})

  return data

# function get video ids
def get_video_ids(playlist_id):

  request=API_connect().playlistItems().list(
                part='contentDetails',
                playlistId=playlist_id,
                maxResults=50)
  response=request.execute()
  video_ids=[]
  for i in range(len(response['items'])):
      video_ids.append(response['items'][i]['contentDetails']['videoId'])


  next_page_token=response.get('nextPageToken')   # more page token use
  more_pages=True

  while more_pages:
      if next_page_token is None:
         more_pages=False

      else:
          request=API_connect().playlistItems().list(
                  part='contentDetails',
                  playlistId=playlist_id,
                  maxResults=50,
                  pageToken=next_page_token)
          response=request.execute()


          for i in range(len(response['items'])):
               video_ids.append(response['items'][i]['contentDetails']['videoId'])


          next_page_token=response.get('nextPageToken')

  return video_ids

# video_details fun
def get_video_details(playlist_id):
  video_ids=get_video_ids(playlist_id)
  all_video_stats=[]
  for i in range(0,len(video_ids),50):
     request=API_connect().videos().list(
        part='snippet,statistics,contentDetails',
        id=','.join(video_ids[i:i+50]))
     response=request.execute()

     for video in response['items']:
          video_stats={"Video_id":video['id'],
                       "Playlist_Id":playlist_id,
                       "Vedio_name":video['snippet']['title'] if 'title' in video['snippet'] else 'not available',
                       "Video_description":video['snippet']['description'] if 'description' in video['snippet'] else 'not available',
                       "Tags":video['snippet']['tags'] if 'tags' in video['snippet'] else 'not available',
                       "PublishedAt":pd.to_datetime(video['snippet']['publishedAt']).strftime('%Y-%m-%d') if 'publishedAt' in video['snippet'] else 'not available',
                       "Views_Count":int(video['statistics']['viewCount'] if 'viewCount' in video['statistics'] else 0),
                       "Likes_Count":int(video['statistics']['likeCount'] if 'likeCount' in video['statistics'] else 0),
                       "Dislike_Count":int(video['statistics']['DislikeCount'] if 'DislikeCount' in video['statistics'] else 0),
                       "Favorite_Count":int(video['statistics']['favoriteCount'] if 'favoriteCount' in video['statistics'] else 0),
                       "Comment_count":int(video['statistics']['commentCount'] if 'commentCount' in video['statistics'] else 0),
                       "Duration":pd.to_timedelta(video['contentDetails']['duration']).total_seconds() if 'duration' in video['contentDetails'] else 'not available',
                       "Thumbnails":video['snippet']['thumbnails']['default']['url'] if 'url' in video['snippet']['thumbnails']['default'] else 'not available',
                       "Caption_status":video['contentDetails']['caption'] if 'caption' in video['contentDetails'] else 'not available'}


          all_video_stats.append(video_stats)

  return all_video_stats

#comment_details fun
def get_comment_details(playlist_id):
     video_ids=get_video_ids(playlist_id)
     comment_details=[]
     for i in video_ids:
          try:
             request=API_connect().commentThreads().list(
                  part='snippet,replies',
                  videoId=i,maxResults=100)

             response=request.execute()
             for comment in response['items']:
              comment_details.append({"Comment_Id": comment['snippet']['topLevelComment']['id'],
                            "Vedio_Id":i,
                           "Comment_Text":comment['snippet']['topLevelComment']['snippet']['textDisplay'],
                           "Comment_Author":comment['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                           "Comment_PublishedAt":pd.to_datetime(comment['snippet']['topLevelComment']['snippet']['publishedAt']).strftime('%Y-%m-%d')
                              })


          except:
             pass
     return comment_details

# one fun get channel all details
def main(channel_id):
  #channel_id=input("Enter the channel id: ")
  c=get_channel_stats(channel_id)
  p=get_playlist(channel_id)
  v=get_video_details(p[0].get('playlist_id'))
  cm=get_comment_details(p[0].get('playlist_id'))

  channel_data={"channel details":c,
                "playlist ids":p,
                "video_details":v,
                "comment details":cm}

  return channel_data 



# FUNCTION TO GET CHANNEL NAMES FROM MONGODB
def channel_names():
    ch_nam=[]
    for i in col.find({}, {'_id': 0, "channel details.channel_name": 1}):
      data=i.values()
      for j in data:
        ch=j[0]
        ch_nam.append(*(ch.values()))

    return ch_nam


# Table Create

cor.execute("""CREATE TABLE if not exists channels(channel_name varchar(50),
channel_id varchar(40) primary key,
subscribers_count bigint,
channel_views_count bigint,
channel_videos_count bigint, 
channel_description varchar(50000),
playlist_id varchar(40))""")
cont.commit() 

cor.execute("""CREATE TABLE if not exists playlists(playlist_id varchar(40) NOT NULL,
channel_id varchar(40),
PRIMARY KEY(playlist_id),
FOREIGN KEY(channel_id) REFERENCES Channels(channel_id))""")
cont.commit()

cor.execute("""CREATE TABLE if not exists Videos(Video_id varchar(20) NOT NULL,
Playlist_Id varchar(40),
Vedio_name varchar(1000),
Video_description varchar(10000),
Tags varchar(5000),
PublishedAt DATE,
Views_Count bigint,
Likes_Count bigint,
Dislike_Count bigint,
Favorite_Count bigint,
Comment_count bigint,
Duration float,
Thumbnails varchar(100),
Caption_status varchar(20),
PRIMARY KEY(Video_id),
FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id))""")
cont.commit()


cor.execute("""CREATE TABLE if not exists comments(Comment_Id varchar(40) PRIMARY KEY,
Vedio_Id varchar(40),
Comment_Text varchar(10000),
Comment_Author varchar(100),
Comment_PublishedAt DATE,
FOREIGN KEY(Vedio_Id) REFERENCES Videos(Video_id))""")
cont.commit()



# HOME PAGE
if selected == "Home":
    col1,col2 = st.columns(2,gap= 'medium')
    col1.markdown("#### :blue[Domain] ")
    col1.markdown(' * 👉 Social Media ')
    col1.markdown("#### :blue[Overview] ")
    col1.markdown(' *  👉Retrieving the Youtube channels data from the Google API, storing it in a MongoDB as data lake, migrating and transforming data into a SQL database,then querying the data and displaying it in the Streamlit app.')
    col1.markdown("#### :blue[Technology Used]")
    col1.markdown(' *:star:  Python***')
    col1.markdown(' *:star:  NOSQL - MongoDB***')
    col1.markdown(' *:star:  SQL - MySql***')
    col1.markdown(' *:star:  Google API integration***')
    col1.markdown(' *:star:  Streamlit - GUI***')
    col2.markdown('### :blue[API Details:] ')
    col2.markdown(' * 👉Here you can find how to get channel_ID from youtube channel please read the below caption to know more about the youtube API :balloon:')
    col2.image("youtubeapi.png")
    col2.info("Please note: Using Google API key we have raise 10000 request per day more request raise an error as Quota Error")
    col2.markdown(' * 👉 Select a particular channel on youtube webpage *:blue[right click on mouse > view page resource]* click on **:blue[ctrl+f]** for find option there you will search for :blue[channelId] there you find like this - ***:blue[UCiEmtpFVJjpvdhsQ2QAhxVA]***')
    col2.markdown("To learn more about Youtube API console please [click here](https://console.developers.google.com) and to visit the Youtube DATA API website [click here](https://developers.google.com/youtube/v3/code_samples/code_snippets) to find use cases .&mdash;\
            :tulip::cherry_blossom::rose::hibiscus::sunflower::blossom:")
   

    # EXTRACT AND TRANSFORM PAGE
if selected == "Extract & Transform":
    tab1,tab2 = st.tabs(["$\huge 📝 EXTRACT $", "$\huge🚀 TRANSFORM $"])

    # EXTRACT TAB
    with tab1:
        st.markdown("#    ")
        st.write("### Enter YouTube Channel_ID below :")
        ch_id = st.text_input(":blue[Hint : Goto channel's home page > Right click > View page source > Find channel_id]").split(',')
        

        if ch_id and st.button("Extract Data"):
          with st.spinner('🤫Please Wait for it...'):
            try:
               details=main(ch_id[0])
               ch_name=(details.get('channel details'))[0].get('channel_name')
               st.write(f'#### Extracted data from :violet["{ch_name}"] channel')
               st.write(details)
            except:
               st.error("Your Channel ID is Not Define")

        if st.button("Upload to MongoDB"):
            with st.spinner('🤫Please Wait for it...'):
                details=main(ch_id[0])
                ch_name=(details.get('channel details'))[0].get('channel_name')
                ch_na=channel_names()
                if ch_name in ch_na:
                    st.error("This Channel details already Uploaded 😥!!", icon='🚨')
                else:
                   col.insert_one(details)
                   st.success("Upload to MogoDB successful !!🤩",icon='📥')




# TRANSFORM TAB
    with tab2:
      st.header(':violet[Data Migrate zone]')
      st.info('''(Note:- This zone specific channel data **Migrate to :blue[PostgreSQL] database from  :green[MongoDB] database** depending on your selection,
                if unavailable your option first collect data.)''')
      st.markdown("#   ")
      st.markdown("### Select a channel to begin Transformation to SQL")
      ch_name=[]
      ch_names = channel_names()
      ch_names.insert(0,'None')
      user_inp = st.selectbox(":blue[Select channel]",options= ch_names)
      

      if user_inp != 'None':
        try:
          def insert_into_channels():
            query = """INSERT INTO channels VALUES(%s,%s,%s,%s,%s,%s,%s)"""
            for i in col.find({"channel details.channel_name" : user_inp},{'_id' : 0,'channel details':1}):
               data=i.values()
               for j in data:
                 ch=j[0]
                 cor.execute(query,tuple(ch.values()))
                 cont.commit()


          def insert_into_playlist():
            query="""INSERT INTO playlists VALUES(%s,%s)"""
            for i in col.find({"channel details.channel_name" : user_inp},{'_id' : 0,'playlist ids':1}):
               data=i.values()
               for j in data:
                 ch=j[0]
                 cor.execute(query,tuple(ch.values()))
                 cont.commit()



          def insert_into_videos():
            query2 = """INSERT INTO videos VALUES(%s,%s,%s,%s,%s,to_date(%s,'yyyy-mm-dd'),%s,%s,%s,%s,%s,%s,%s,%s)"""
            for i in col.find({"channel details.channel_name" : user_inp},{'_id' : 0,'video_details':1}):
                data=i.values()
                for j in data:
                   for k in j:
                      cor.execute(query2,tuple(k.values()))
                      cont.commit()
    


          def insert_into_comments():
            query3 = """INSERT INTO comments VALUES(%s,%s,%s,%s,to_date(%s,'yyyy-mm-dd'))"""
            for i in col.find({"channel details.channel_name" : user_inp},{'_id' : 0,'comment details':1}):
                data=i.values()
                for j in data:
                   for k in j:
                     cor.execute(query3,tuple(k.values()))
                     cont.commit()
            st.success("Transformation to PostgreSQL Successful 🤩!!",icon='📥')

          insert_into_channels()
          insert_into_playlist()
          insert_into_videos()
          insert_into_comments()
         
        except:
           st.error("This Channel details already Transformed !!", icon='🚨')
      else:
         st.error("You are choose a Channel Name Please😥!!!")

# VIEW PAGE
if selected == "View":
        st.header(' :violet[Channels Analysis Zone]')
        st.info('''(Note:- This zone **Analysis of a collection of channel data** depends on your question selection and gives a table format output.)''')
        st.write("### :orange[Select any question to get Insights]")
        Questions=st.selectbox(':blue[Select your Questions]',['None','1. What are the names of all the videos and their corresponding channels?',
         '2. Which channels have the most number of videos, and how many videos do they have?',
         '3. What are the top 10 most viewed videos and their respective channels?',
         '4. How many comments were made on each video, and what are their corresponding video names?',
         '5. Which videos have the highest number of likes, and what are their corresponding channel names?',
         '6. What is the total number of likes and dislikes for each video, and what are their corresponding video names?',
         '7. What is the total number of views for each channel, and what are their corresponding channel names?',
         '8. What are the names of all the channels that have published videos in the year 2022?',
         '9. What is the average duration of all videos in each channel, and what are their corresponding channel names?',
        '10. Which videos have the highest number of comments, and what are their corresponding channel names?'])

        if Questions and st.button('Submit'):
          st.success('🤩 Done') 
          if Questions=='1. What are the names of all the videos and their corresponding channels?':
             cor.execute("""SELECT vedio_name,channel_name  
                            FROM videos full outer join channels on videos.playlist_id=channels.playlist_id
                            ORDER BY channel_name""")
             df = pd.DataFrame(cor.fetchall())
             df_new=df.rename(columns={0:'video_name',1:'channel_name'}) 
             st.write(df_new)

          elif Questions == '2. Which channels have the most number of videos, and how many videos do they have?':
            cor.execute("""SELECT channel_name,channel_videos_count
                           FROM channels
                           ORDER BY channel_videos_count DESC""")
            df = pd.DataFrame(cor.fetchall())
            df_new=df.rename(columns={0:'channel_name',1:'video_count'})
            st.write(df_new)

          elif Questions == '3. What are the top 10 most viewed videos and their respective channels?':
            cor.execute("""SELECT channel_name,vedio_name,views_count
                           FROM videos full outer join channels on videos.playlist_id=channels.playlist_id
                           ORDER BY views_count DESC
                           LIMIT 10""")
            df = pd.DataFrame(cor.fetchall())
            df_new=df.rename(columns={0:'channel_name',1:'video_name',2:'video_views_count'})
            st.write(df_new)

          elif Questions == '4. How many comments were made on each video, and what are their corresponding video names?':
           cor.execute("""SELECT vedio_name,comment_count 
                          FROM videos 
                          ORDER BY comment_count DESC""")
           df = pd.DataFrame(cor.fetchall())
           df_new=df.rename(columns={0:'video_name',1:'video_comment_count'})
           st.write(df_new)

          elif Questions == '5. Which videos have the highest number of likes, and what are their corresponding channel names?':
           cor.execute("""SELECT channel_name,vedio_name,likes_count
                          FROM videos full outer join channels on videos.playlist_id=channels.playlist_id
                          ORDER BY likes_count DESC
                          LIMIT 10""")
           df = pd.DataFrame(cor.fetchall())
           df_new=df.rename(columns={0:'channels_name',1:'video_name',2:'video_likes_count'})
           st.write(df_new)

          elif  Questions == '6. What is the total number of likes and dislikes for each video, and what are their corresponding video names?':
            cor.execute("""SELECT vedio_name,likes_count,dislike_count
                          FROM videos
                          ORDER BY vedio_name""")
            df = pd.DataFrame(cor.fetchall())
            df_new=df.rename(columns={0:'video_name',1:'video_likes_count',2:'dislike_count'})
            st.write(df_new)


          elif  Questions == '7. What is the total number of views for each channel, and what are their corresponding channel names?':
             cor.execute("""SELECT channel_name,channel_views_count
                            FROM channels
                            ORDER BY channel_views_count DESC""")
             df = pd.DataFrame(cor.fetchall())
             df_new=df.rename(columns={0:'channel_name',1:'channel_views_count'})
             st.write(df_new)

          elif Questions == '8. What are the names of all the channels that have published videos in the year 2022?':
                cor.execute("""SELECT channels.channel_name 
                               FROM channels full outer join videos on videos.playlist_id=channels.playlist_id 
                               WHERE publishedat between '2022-01-01' and '2022-12-31' 
                               GROUP BY channel_name 
                               ORDER BY channel_name""")
                df = pd.DataFrame(cor.fetchall())
                df_new=df.rename(columns={0:'channel_name'})
                st.write(df_new)

          elif Questions == '9. What is the average duration of all videos in each channel, and what are their corresponding channel names?':
              cor.execute("""SELECT channels.channel_name,
                             AVG(duration)
                             FROM videos full outer join channels on videos.playlist_id=channels.playlist_id
                             GROUP BY channel_name
                             ORDER BY AVG(duration) DESC""")
              df = pd.DataFrame(cor.fetchall())
              df_new=df.rename(columns={0:'channel_name',1:'average_videos_duration_seconds'})
              st.write(df_new)

          elif Questions == '10. Which videos have the highest number of comments, and what are their corresponding channel names?':
              cor.execute("""SELECT channel_name,vedio_name,comment_count
                             FROM videos full outer join channels on videos.playlist_id=channels.playlist_id
                             ORDER BY comment_count DESC
                             LIMIT 10""")
              df = pd.DataFrame(cor.fetchall())
              df_new=df.rename(columns={0:'channel_name',1:'video_name',2:'comment_count'})
              st.write(df_new)
        elif Questions == 'None':
           st.error('You are Not selected Questions😥!!!')


