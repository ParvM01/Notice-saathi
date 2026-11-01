def generate_notice_explanation(notice):
    """
    Temporary mock response for testing the AI integration.

    This does not interpret the actual notice document.
    Replace this provider with Gemini integration later.
    """

    return {
        "mode": "mock",
        "is_ai_generated": False,
        "notice_id": notice["id"],
        "notice_title": notice["title"],
        "category": notice["category"],
        "hinglish_explanation": (
            "Yeh NoticeSaathi ka temporary preview hai. "
            "Abhi Gemini AI connect nahi hua hai, isliye "
            "notice ka actual content analyse nahi kiya gaya hai."
        ),
        "student_action": (
            "Original official notice ko open karke uski "
            "details aur instructions carefully check karein."
        ),
        "official_url": notice["url"],
        "important_note": (
            "Yeh AI-generated explanation nahi hai. "
            "Final information ke liye official notice hi dekhein."
        )
    }