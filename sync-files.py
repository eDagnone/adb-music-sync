from ppadb.client import Client as AdbClient

import subprocess
import os
import concurrent.futures

PHONE_MUSIC_PATH = "/storage/emulated/0/music"
PC_MUSIC_PATH = os.path.expanduser('~') + "/Music"

def get_adb_device():
    subprocess.call(['adb', 'start-server'])
    client = AdbClient(host="127.0.0.1", port=5037)
    device = None
    while device is None:
        devices = client.devices()
        if devices == []:
            input('No Devices. Please plug in a device and presss enter.')
        else:
            print(devices)
            device = devices[0]
            print("Device connected with serial", device.serial)
    return device


class FileObject:
    def __init__(self, timestamp, size, name):
        self.timestamp = int(timestamp)
        self.size = int(size)
        self.name = name
    def print_readable(self):
        print(f"Timestamp: {self.timestamp}, Size: {self.size}, Name: {self.name}")

def parse_adb_output(output):
    lines = output.split('\n')
    adb_objects = []

    for line in lines:
        if line and line != "stat: '*.*': No such file or directory":
            timestamp = line[:10]
            size_start = 10
            size_end = line.find(' ', size_start)
            size = line[size_start:size_end]
            name = line[size_end+1:].strip()
            
            adb_object = FileObject(timestamp, size, name)
            adb_objects.append(adb_object)

    return adb_objects

def get_files_info(directory_path):
    file_objects = []

    for filename in os.listdir(directory_path):
        filepath = os.path.join(directory_path, filename)

        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            last_modified = os.path.getmtime(filepath)

            file_object = FileObject(last_modified, size, filename)
            file_objects.append(file_object)

    return file_objects


def pull_file(device, timestamp, filename, reason):
    print(reason, "\tPulling to PC:", filename)
    full_phone_path = PHONE_MUSIC_PATH + "/" + filename
    full_pc_path = PC_MUSIC_PATH + "/" + filename
    device.pull(full_phone_path, full_pc_path)
    os.utime(full_pc_path, (timestamp, timestamp))

def push_file(device, filename, reason):
    print(reason, "\tPushing to phone:", filename)
    full_phone_path = PHONE_MUSIC_PATH + "/" + filename
    full_pc_path = PC_MUSIC_PATH + "/" + filename
    device.push(full_pc_path, full_phone_path)



device = get_adb_device()
songs_stat = device.shell(f"cd {PHONE_MUSIC_PATH} && stat -c '%Y%s %n' *.*")
phone_files = parse_adb_output(songs_stat)
pc_files = get_files_info(PC_MUSIC_PATH)

phone_dict = {file.name: file for file in phone_files}
pc_dict = {file.name: file for file in pc_files}

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = []
    
    # TO PC / In Both Places
    for phone_file in phone_files:
        filename = phone_file.name
        pc_file = pc_dict.get(filename)
        if pc_file: #If the file is in both places
            if phone_file.size > pc_file.size:
                futures.append(executor.submit(pull_file, device, phone_file.timestamp, filename, "CORRPT"))
            elif phone_file.size < pc_file.size:
                futures.append(executor.submit(push_file, device, filename, "CORRPT"))
            elif phone_file.timestamp > pc_file.timestamp:
                futures.append(executor.submit(pull_file, device, phone_file.timestamp, filename, "NEWER"))
            elif phone_file.timestamp < pc_file.timestamp:
                futures.append(executor.submit(push_file, device, filename, "NEWER"))
        else:
            futures.append(executor.submit(pull_file, device, phone_file.timestamp, filename, "NEW"))
            

    # TO PHONE
    for pc_file in pc_files:
        phone_file = phone_dict.get(pc_file.name)
        if not phone_file:
            futures.append(executor.submit(push_file, device, pc_file.name, "NEW"))
    

    print("Waiting for sync. Do not unplug.")
    concurrent.futures.wait(futures)
subprocess.call(['adb', 'kill-server'])
print("Done!")

#Multithreading is 15% faster, for some reason.

#TODO: ADB issue rescan. Something about dev tools, Media-Provider
