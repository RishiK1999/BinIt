
#Libraries
import RPi.GPIO as GPIO
import datetime
import time
from twilio.rest import Client
import pandas

##Twilio account login credentials
account_sid = 'ACfa4fb2a8b424016de26f4704e4f74f25'
auth_token = '62a0e14ecf4317bc1caf67752216eab1'
client = Client(account_sid, auth_token)

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)

##Global variables
global fullDist
global outputDate
global outputTime
global isFull
global isEmpty
global currentdate
currentdate = "None"

#set GPIO Pins on Raspberry Pi
GPIO_TRIGGER = 18
GPIO_ECHO = 24
 
#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
GPIO.setup(25, GPIO.OUT)

##Except error warnings due to infinite loop
GPIO.setwarnings(False)

#Calculates distance to object based on difference in time between emitted and received ultrasonic wave
def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    # record times for emitted and received ultrasonic wave
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
    
    # return calcualted value
    return distance

#uses Twilio API to send SMS to garbage collecting personnel
def message():
    message = client.api.account.messages.create(
            to="+16475151794",
            from_="+16475572916", 
            body="Dumpster is FULL!"
   ) 

if __name__ == '__main__':
    try:
        # distance to treat as garbage is full when readings are below it
        fullDist=10.0
        
        # array to store last 5 readings to calculate average to account for fluctuations
        valueList = [0,0,0,0,0]
        
        # set initial parameters
        i = 0
        test = True
        isFull=False
        isEmpty=True
        messageFlag = False
        
        #initialize table in text file to store data
        df = pandas.DataFrame([['-', '-', 0.0, 0, 0]], columns=['outputDate', 'outputTime', 'fullDist', 'isFull', 'isEmpty'])
        
        #turn off LED if ON
        GPIO.output(25,GPIO.LOW)
        
        # infinite loop to check for when garbage is full
        while True:
            
            # sleep thread for 1 reading per 5 seconds
            time.sleep(5)
            
            #calculate distance to garbage level 
            dist = distance()
            
            #store date and time of reading to the second
            outputDate = datetime.datetime.today().strftime("%Y-%m-%d")
            outputTime = datetime.datetime.today().strftime("%H:%M:%S")
            
            print ("Measured Distance = %.1f cm" % dist)
            
            # check if dumpster was emptied recently
            if (dist<=27):
                isEmpty = False
            
            # account for reading fluctuations by taking average of last 5 readings. If past full garbage level, send message that dumpster is full and light up LED
            valueList[i]=dist
            value1 = sum(valueList)/len(valueList) +1;
            value2 = sum(valueList)/len(valueList) -1;
            test = True
            if (value1 <= fullDist and value2 <= fullDist):
                for j in range(5):
                    if (valueList[j] <= value2 or valueList[j]>=value1):
                        test = True
                if (test==True):
                    print("Trash Can has reached full capacity. Disposal needed!")
                    isFull = True
                    if outputDate != currentdate:                            # flag variable triggered only for one message per day
                        messageFlag = True
                        currentdate = datetime.datetime.today().strftime("%Y-%m-%d")
                    GPIO.output(25,GPIO.HIGH)
            
            # dataframe for measurements
            df = df.append({"outputDate" : outputDate, "outputTime" : outputTime, "fullDist" : fullDist, "isFull" : isFull, "isEmpty" : isEmpty}, ignore_index=True)
            
            # resets flag pointer and sends message
            if messageFlag == True:
                message()
                messageFlag = False
            
            # post increment for average of 5 readings
            i+=1
            if (i==5):
                i=0
                
    # Reset by pressing CTRL + C to end program
    except KeyboardInterrupt:
        # print measurements to .xlsx file for analysis and bookeeping purposes
        df.to_excel("output.xlsx")
        
        print("Measurement stopped by User")
        
        # cleansup ports that were used by Raspberry Pi
        GPIO.cleanup()
