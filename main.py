import json
import random
import time
from datetime import datetime, timedelta

from instagrapi import Client
from langdetect import detect
import schedule

# ========== تنظیمات ==========
MIN_FOLLOW = 20
MAX_FOLLOW = 30
HASHTAGS = ["خنده", "طنز", "ایران", "بازیگر", "تهران", "عاشقانه", "پسرونه", "دخترونه"]
FOLLOWED_FILE = "followed.json"

# ========== ورود دستی ==========
USERNAME = input("Instagram Username: ")
PASSWORD = input("Instagram Password: ")

cl = Client()
cl.login(USERNAME, PASSWORD)

# ========== ذخیره و بارگذاری ==========
def load_followed():
    try:
        with open(FOLLOWED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_followed(data):
    with open(FOLLOWED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== تشخیص پیج ایرانی ==========
def is_persian(text):
    try:
        return detect(text) == "fa"
    except:
        return False

def find_target_accounts():
    found = set()
    for tag in random.sample(HASHTAGS, 3):
        medias = cl.hashtag_medias_recent(tag, amount=30)
        for media in medias:
            user = media.user
            if user.pk in found or user.is_private:
                continue
            try:
                info = cl.user_info(user.pk)
                if info.follower_count >= 20000 and is_persian(info.biography):
                    found.add(user.pk)
            except:
                continue
    return list(found)

# ========== انتخاب و فالو ==========
def follow_users():
    followed = load_followed()
    targets = find_target_accounts()
    count = random.randint(MIN_FOLLOW, MAX_FOLLOW)

    print(f"🎯 Found {len(targets)} potential pages.")

    followed_today = 0
    for target_pk in targets:
        followers = cl.user_followers(target_pk, amount=100)
        for user_id, user in followers.items():
            if any(f["user_id"] == user_id for f in followed):
                continue
            try:
                cl.user_follow(user_id)
                print(f"✅ Followed: {user.username}")
                followed.append({
                    "user_id": user_id,
                    "username": user.username,
                    "follow_time": datetime.now().isoformat()
                })
                followed_today += 1
                time.sleep(random.randint(30, 90))  # طبیعی جلوه بده
                if followed_today >= count:
                    break
            except Exception as e:
                print(f"❌ Error: {e}")
        if followed_today >= count:
            break

    save_followed(followed)

# ========== آنفالو اتومات ==========
def unfollow_users():
    followed = load_followed()
    updated = []
    for f in followed:
        uid = f["user_id"]
        follow_time = datetime.fromisoformat(f["follow_time"])
        try:
            friendship = cl.user_friendship(uid)
            now = datetime.now()

            # اگر 1 روز گذشته و فالو نکردن → آنفالو
            if not friendship.followed_by and now - follow_time >= timedelta(days=1):
                cl.user_unfollow(uid)
                print(f"❌ Unfollowed (did not follow back): {f['username']}")
                continue

            # اگر 3 روز گذشته → حتما آنفالو
            if now - follow_time >= timedelta(days=3):
                cl.user_unfollow(uid)
                print(f"🔁 Unfollowed after 3 days: {f['username']}")
                continue

            updated.append(f)
        except:
            continue

    save_followed(updated)

# ========== زمان‌بندی اجرا ==========
schedule.every().day.at("10:00").do(follow_users)
schedule.every().day.at("21:00").do(unfollow_users)

print("🤖 Bot started and scheduled.")

while True:
    schedule.run_pending()
    time.sleep(30)
