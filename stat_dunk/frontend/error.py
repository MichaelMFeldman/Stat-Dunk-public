from datetime import datetime

def write_error(msg):
    output = open("error_log.txt", 'a')
    current_time = datetime.now()
    output.write("{}-{}-{}  {}:{}:{} {}".format(
        current_time[0], current_time[1], current_time[2],
        current_time[3], current_time[4], current_time[5], 
        msg))
    output.close()