import requests

url = "http://172.28.0.12:5000/align_lyrics"
audio_path = "/home/cao-le/Music/y2mate.com - Lemon Tree.mp3"  # Replace with your actual audio file path

with open(audio_path, "rb") as f:
    files = {"audio_file": f}
    data = {
        "lyrics": """I'm sittin' here in the boring room
It's just another rainy Sunday afternoon
I'm wastin' my time, I got nothin' to do
I'm hangin' around, I'm waitin' for you
But nothing ever happens
And I wonder

[Verse 2]
I'm drivin' around in my car
I'm drivin' too fast, I'm drivin' too far
I'd like to change my point of view
I feel so lonely, I'm waitin' for you
But nothing ever happens
And I wonder

[Chorus]
I wonder how, I wonder why
Yesterday, you told me 'bout the blue, blue sky
And all that I can see is just a yellow lemon tree
I'm turnin' my head up and down
I'm turnin', turnin', turnin', turnin', turnin' around
And all that I can see is just another lemon tree

[Post-Chorus]
Sing
Dap, da-da-da-dam, di-dap-da
Da-da-da-dam, di-dap-da
Dap, di-di-li-da

[Verse 3]
I'm sittin' here, I missed the power
I'd like to go out, takin' a shower
But there's a heavy cloud inside my head
I feel so tired, put myself into bed
Well, nothing ever happens
And I wonder

[Bridge]
Isolation is not good for me
Isolation, I don't want to sit on the lemon tree

[Verse 4]
I'm steppin' around in the desert of joy
Maybe, anyhow, I'll get another toy
And everything will happen
And you wonder

[Chorus]
I wonder how, I wonder why
Yesterday, you told me 'bout the blue, blue sky
And all that I can see is just another lemon tree
I'm turnin' my head up and down
I'm turnin', turnin', turnin', turnin', turnin' around
And all that I can see is just a yellow lemon tree
And I wonder, wonder, I wonder how, I wonder why
Yesterday, you told me 'bout the blue, blue sky
And all that I can see (Ah, dip-dip-dip-dip)
And all that I can see (Ah, dip-dip-dip-dip)
And all that I can see
Is just a yellow lemon tree"""
    }
    response = requests.post(url, files=files, data=data)

print(response.json())