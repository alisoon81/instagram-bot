import json
import random
import time
from datetime import datetime, timedelta
from instagrapi import Client
from langdetect import detect
import schedule
import os

# ========== تنظیمات ==========
MIN_FOLLOW = 15
MAX_FOLLOW = 35
HASHTAGS = ["خنده", "طنز", "ایران", "بازیگر", "تهران", "عاشقانه", "پسرونه", "دخترونه"]
FOLLOWED_FILE = "followed.json"
PROXY = None  # مثلا "http://username:password@proxy_ip:port" اگر داری پراکسی بذار اینجا

# ========== ورود دستی ==========
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")


cl = Client()
if PROXY:
    cl.set_proxy(PROXY)
cl.login(USERNAME, PASSWORD)


def random_sleep(min_sec=60, max_sec=180):
    delay = random.uniform(min_sec, max_sec)
    print(f"🕒 Sleeping for {int(delay)} seconds to look natural...")
    time.sleep(delay)


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
        try:
            medias = cl.hashtag_medias_recent(tag, amount=30)
        except Exception as e:
            print(f"Error fetching hashtag {tag}: {e}")
            continue
        for media in medias:
            user = media.user
            if user.pk in found or user.is_private:
                continue
            try:
                info = cl.user_info(user.pk)
                if info.follower_count >= 20000 and is_persian(info.biography):
                    found.add(user.pk)
            except Exception as e:
                print(f"Error fetching user info: {e}")
                continue
    return list(found)


def get_daily_follow_limit():
    return random.randint(MIN_FOLLOW, MAX_FOLLOW)


# ========== لایک کردن چند پست ==========
def like_some_posts(user_id, max_likes=2):
    try:
        medias = cl.user_medias(user_id, 10)
    except Exception as e:
        print(f"Error getting user medias: {e}")
        return

    likes = 0
    for media in medias:
        if likes >= max_likes:
            break
        try:
            cl.media_like(media.pk)
            print(f"❤️ Liked media {media.pk} from user {user_id}")
            likes += 1
            random_sleep(10, 30)
        except Exception as e:
            print(f"Error liking media: {e}")
            continue


# ========== انتخاب و فالو ==========
def follow_users():
    followed = load_followed()
    targets = find_target_accounts()
    count = get_daily_follow_limit()

    print(f"🎯 Found {len(targets)} potential pages.")
    print(f"👣 Planning to follow {count} users today.")

    followed_today = 0
    for target_pk in targets:
        try:
            followers = cl.user_followers(target_pk, amount=100)
        except Exception as e:
            print(f"Error getting followers: {e}")
            continue

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

                # لایک چند پست برای طبیعی‌تر بودن
                like_some_posts(user_id)

                followed_today += 1
                random_sleep(60, 180)  # استراحت طولانی‌تر برای طبیعی بودن

                if followed_today >= count:
                    break
            except Exception as e:
                err_str = str(e).lower()
                print(f"❌ Error: {e}")
                if "challenge_required" in err_str or "blocked" in err_str:
                    print("⚠️ Possible block detected. Stopping the bot for today.")
                    return  # قطع اجرای ربات
                continue
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
                random_sleep(60, 180)
                continue

            # اگر 3 روز گذشته → حتما آنفالو
            if now - follow_time >= timedelta(days=3):
                cl.user_unfollow(uid)
                print(f"🔁 Unfollowed after 3 days: {f['username']}")
                random_sleep(60, 180)
                continue

            updated.append(f)
        except Exception as e:
            print(f"Error during unfollow: {e}")
            continue

    save_followed(updated)


# ========== زمان‌بندی اجرا ==========
schedule.every().day.at("10:00").do(follow_users)
schedule.every().day.at("21:00").do(unfollow_users)

print("🤖 Bot started and scheduled.")

while True:
    schedule.run_pending()
    time.sleep(30)
