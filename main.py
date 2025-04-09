 

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode

from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import tweepy

# 1. 加载环境变量
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# 2. 日志配置
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 3. 初始化 Tweepy 客户端（Twitter API v2）
twitter_client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN, wait_on_rate_limit=True)

# 4. /start 命令处理
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 欢迎使用 TwitterNewsBot！\n"
        "使用命令 /twitternews <关键词> 获取 Twitter 上最热门的相关推文。"
    )

# 5. /twitternews 命令处理
async def twitternews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗️ 请在命令后提供关键词，例如：`/twitternews Python`", parse_mode=ParseMode.MARKDOWN)
        return

    keyword = " ".join(context.args)
    await update.message.reply_text(f"🔍 正在搜索关键词：{keyword}，请稍候...")

    try:
        # 调用 Recent Search Endpoint，按热门度排序（popularity 排序需企业版，此处用默认时间排序，后续可按 retweet_count 自行筛选）
        tweets = twitter_client.search_recent_tweets(
            query=keyword + " -is:retweet lang:en",
            tweet_fields=["public_metrics", "created_at", "author_id", "text"],
            user_fields=["username", "name"],
            expansions=["author_id"],
            max_results=10  # 最多获取 10 条
        )

        if not tweets.data:
            await update.message.reply_text("⚠️ 未找到相关推文。")
            return

        # 将推文按转发数 + 点赞数排序，选出最“火”的一条
        tweets_list = []
        for t in tweets.data:
            metrics = t.public_metrics
            score = metrics["retweet_count"] + metrics["like_count"] + metrics["reply_count"] + metrics["quote_count"]
            tweets_list.append((t, score))
        top_tweet, top_score = max(tweets_list, key=lambda x: x[1])

        # 获取作者信息
        user_map = {u["id"]: u for u in tweets.includes["users"]}
        author = user_map[top_tweet.author_id]

        # 构造消息
        msg = (
            f"🔥 *最热门推文*\n\n"
            f"*作者*：{author['name']} (@{author['username']})\n"
            f"*发布时间*：{top_tweet.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"*转发*：{top_tweet.public_metrics['retweet_count']}  |  *点赞*：{top_tweet.public_metrics['like_count']}\n\n"
            f"{top_tweet.text}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in twitternews: {e}")
        await update.message.reply_text("❌ 获取推文时出错，请稍后重试。")

# 6. 主函数：启动 Bot
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("twitternews", twitternews))

    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
