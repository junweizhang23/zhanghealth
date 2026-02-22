"""
Message templates for health reminders.
Provides age-appropriate exercise instructions in both English and Chinese.
"""

import random
from datetime import datetime

# ---------------------------------------------------------------------------
# Exercise plans keyed by plan name.
# Each plan contains a list of daily routines that rotate.
# ---------------------------------------------------------------------------

EXERCISE_PLANS = {
    # Plan for 60+ age group: gentle, progressive, safety-focused
    "senior_beginner": [
        {
            "title": "平板支撑 + 轻量训练 (Day A)",
            "exercises": [
                "🧘 平板支撑 (Plank): 从膝盖跪姿开始，保持20秒 x 3组，组间休息30秒",
                "💪 墙壁俯卧撑 (Wall Push-ups): 面对墙壁，双手撑墙，做10次 x 2组",
                "🦵 椅子辅助深蹲 (Chair Squats): 慢慢坐下再站起，10次 x 2组",
                "🏋️ 轻哑铃弯举 (Light Dumbbell Curls): 2-3磅，每侧10次 x 2组",
            ],
            "tips": "⚠️ 注意：动作要慢，呼吸要稳。如果感到头晕或疼痛，请立即停止。",
        },
        {
            "title": "平衡 + 核心训练 (Day B)",
            "exercises": [
                "🧘 平板支撑 (Plank): 膝盖跪姿，保持25秒 x 3组",
                "🦶 单脚站立 (Single Leg Stand): 扶椅子，每侧15秒 x 3次",
                "🏋️ 轻哑铃侧举 (Lateral Raises): 2磅，每侧8次 x 2组",
                "🚶 原地踏步 (Marching in Place): 抬高膝盖，2分钟",
            ],
            "tips": "⚠️ 确保周围有稳固的支撑物。慢慢来，安全第一！",
        },
        {
            "title": "上肢 + 柔韧性 (Day C)",
            "exercises": [
                "🧘 平板支撑 (Plank): 膝盖跪姿，保持30秒 x 3组",
                "💪 弹力带划船 (Resistance Band Rows): 10次 x 2组",
                "🏋️ 轻哑铃推举 (Overhead Press): 2磅，8次 x 2组",
                "🧘 坐姿拉伸 (Seated Stretches): 每个动作保持15秒",
            ],
            "tips": "⚠️ 拉伸时不要弹跳，保持稳定的拉伸感即可。",
        },
    ],
    # Plan for 40-year-old: more challenging
    "adult_intermediate": [
        {
            "title": "核心 + 力量 (Day A)",
            "exercises": [
                "🧘 平板支撑 (Plank): 标准姿势 45秒 x 4组",
                "💪 俯卧撑 (Push-ups): 15次 x 3组",
                "🦵 深蹲 (Squats): 20次 x 3组",
                "🏋️ 哑铃弯举 (Dumbbell Curls): 15磅，12次 x 3组",
            ],
            "tips": "💡 保持核心收紧，注意呼吸节奏。",
        },
        {
            "title": "全身训练 (Day B)",
            "exercises": [
                "🧘 侧平板支撑 (Side Plank): 每侧30秒 x 3组",
                "🏋️ 硬拉 (Deadlifts): 适当重量，10次 x 3组",
                "💪 引体向上或弹力带辅助 (Pull-ups): 8次 x 3组",
                "🚴 开合跳 (Jumping Jacks): 30秒 x 3组",
            ],
            "tips": "💡 硬拉注意保持背部平直，不要弓背。",
        },
    ],
}

# ---------------------------------------------------------------------------
# Greeting and motivational phrases
# ---------------------------------------------------------------------------

GREETINGS_CN = [
    "早上好！",
    "你好！",
    "新的一天，新的开始！",
    "今天也要加油哦！",
    "美好的一天从运动开始！",
]

MOTIVATIONS_CN = [
    "坚持就是胜利！每一次锻炼都在让身体更强壮 💪",
    "运动是最好的投资，您的身体会感谢您的 ❤️",
    "慢慢来，比不做强！您做得很棒 👍",
    "健康是最大的财富，继续保持！🌟",
    "每一步都算数，您正在变得更健康 🎯",
]

CONFIRMATION_PROMPT = "\n\n✅ 做完了请回复 OK\n❌ 如需暂停提醒请回复 NO"


def get_exercise_message(user_name: str, plan_name: str, message_index: int = 0) -> str:
    """
    Generate a personalized exercise reminder message.

    Args:
        user_name: The recipient's name.
        plan_name: The exercise plan key (e.g., "senior_beginner").
        message_index: Used to rotate through different routines.

    Returns:
        A formatted message string ready to send via SMS.
    """
    plan = EXERCISE_PLANS.get(plan_name, EXERCISE_PLANS["senior_beginner"])
    routine = plan[message_index % len(plan)]

    greeting = random.choice(GREETINGS_CN)
    motivation = random.choice(MOTIVATIONS_CN)

    lines = [
        f"{greeting} {user_name}，",
        f"",
        f"📋 今天的锻炼计划: {routine['title']}",
        f"",
    ]

    for exercise in routine["exercises"]:
        lines.append(f"  {exercise}")

    lines.extend(
        [
            f"",
            routine["tips"],
            f"",
            motivation,
            CONFIRMATION_PROMPT,
        ]
    )

    return "\n".join(lines)


def get_opt_out_confirmation(user_name: str) -> str:
    """Message sent when a user opts out."""
    return (
        f"{user_name}，已收到您的请求。提醒已暂停。\n\n"
        f"如果以后想重新开始，随时回复 START 即可。\n"
        f"祝您健康快乐！❤️"
    )


def get_opt_in_confirmation(user_name: str) -> str:
    """Message sent when a user opts back in."""
    return (
        f"太好了 {user_name}！欢迎回来！\n\n"
        f"提醒已重新开启，我们会继续每隔一天给您发送锻炼提醒。\n"
        f"一起加油！💪"
    )


def get_ok_acknowledgment(user_name: str) -> str:
    """Message sent when a user confirms they completed their exercise."""
    responses = [
        f"👏 太棒了 {user_name}！今天的锻炼完成了，继续保持！",
        f"💪 好样的 {user_name}！坚持锻炼，身体会越来越好！",
        f"🌟 {user_name} 真厉害！又完成了一天的锻炼！",
        f"❤️ {user_name}，做得好！休息一下，明天继续加油！",
    ]
    return random.choice(responses)
