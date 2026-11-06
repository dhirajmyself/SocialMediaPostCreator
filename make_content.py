"""Builds Health_Content.xlsx. Facts are paraphrased from WHO / NHS pages (URL kept per row).
Always re-check each row against its source before publishing."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from engine import DEF_TAGS, TEMPLATES

WHO_D = "https://www.who.int/news-room/fact-sheets/detail/healthy-diet"
WHO_PA = "https://www.who.int/news-room/fact-sheets/detail/physical-activity"
WHO_SALT = "https://www.who.int/news-room/fact-sheets/detail/salt-reduction"
NHS5 = "https://www.nhs.uk/live-well/eat-well/5-a-day/why-5-a-day/"
NHSW = "https://www.nhs.uk/live-well/eat-well/water-drinks-nutrition/"
NHSS = "https://www.nhs.uk/every-mind-matters/mental-health-issues/sleep/"
NHSM = "https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/five-steps-to-mental-wellbeing/"
NHSH = "https://www.nhs.uk/live-well/healthy-weight/"
OWN = "Original (no factual claim)"
HT, MQ, DYK, NF, MF, CL, ST, WR = TEMPLATES

# (Category, Headline, Main content, Supporting tip, Source, Style)
R = [
 ("Nutrition", "Eat Your 5 A Day", "Aim for at least 5 portions of a variety of fruit and vegetables each day. Fresh, frozen, canned, dried and juiced options can all count.", "Add one extra portion to a meal you already eat.", NHS5, HT),
 ("Nutrition", "400 Grams a Day", "WHO advises eating at least 400 g (five portions) of fruit and vegetables a day. Potatoes, sweet potatoes and cassava do not count.", "Include veg at lunch and dinner.", WHO_D, NF),
 ("Nutrition", "Go Easy on Salt", "WHO recommends adults eat less than 5 g of salt a day, about one teaspoon.", "Season with herbs and spices instead.", WHO_SALT, DYK),
 ("Nutrition", "Limit Free Sugars", "WHO recommends keeping free sugars to less than 10% of total energy intake.", "Check labels on drinks, cereals and sauces.", WHO_D, NF),
 ("Nutrition", "Frozen Veg Counts", "Myth: Frozen vegetables do not count towards your 5 A Day. Fact: Fresh, frozen, canned and dried fruit and vegetables can all count.", "Keep a bag of frozen veg handy.", NHS5, MF),
 ("Nutrition", "Choose Wholegrains", "A healthy diet includes whole grains such as oats, brown rice and wholewheat bread; unprocessed maize and millet also count.", "Swap one refined grain for a wholegrain today.", WHO_D, HT),
 ("Fitness", "Move Every Week", "WHO recommends adults do 150 to 300 minutes of moderate-intensity aerobic activity each week.", "Break it up: 30 minutes on 5 days.", WHO_PA, DYK),
 ("Fitness", "Strength Matters", "Adults should also do muscle-strengthening activities on 2 or more days a week.", "Try bodyweight squats or resistance bands.", WHO_PA, HT),
 ("Fitness", "Sit Less, Move More", "WHO advises limiting time spent sitting and replacing it with physical activity of any intensity.", "Set a reminder to stand and move regularly.", WHO_PA, WR),
 ("Fitness", "Some Is Better Than None", "Some physical activity is better than none. Start small and build up gradually.", "Begin with a 10-minute walk.", WHO_PA, HT),
 ("Fitness", "No Gym Needed", "Myth: You need a gym membership to be active. Fact: Walking, cycling, dancing and active play all count as physical activity.", "Pick an activity you enjoy.", WHO_PA, MF),
 ("Weight Management", "Habits Over Crash Diets", "Small, steady changes to eating and activity are easier to keep up than crash diets.", "Choose just one change this week.", NHSH, HT),
 ("Weight Management", "Energy Balance", "WHO notes that energy intake should be in balance with energy used, to avoid unhealthy weight gain.", "Pair mindful eating with regular movement.", WHO_D, DYK),
 ("Weight Management", "Plan Your Shopping", "Planning meals ahead and shopping from a list can make healthy eating easier; check food labels as you go.", "Write your list before you shop.", NHSH, CL),
 ("Weight Management", "Your Healthy Weight Is Personal", "A healthy weight differs from person to person. A GP or other healthcare professional can give advice that is right for you.", "Book a check-up if you have questions.", NHSH, WR),
 ("Sleep", "How Much Sleep?", "Most adults need about 6 to 9 hours of sleep a night.", "Notice how rested you feel and adjust.", NHSS, DYK),
 ("Sleep", "Keep a Routine", "Going to bed and waking up at similar times each day helps support your body clock.", "Choose a realistic bedtime.", NHSS, HT),
 ("Sleep", "Wind Down", "A relaxing routine before bed, such as a warm bath, reading or gentle stretching, can help you drift off.", "Start 30 minutes before bed.", NHSS, ST),
 ("Sleep", "Cool, Dark and Quiet", "Keep your bedroom cool, dark and quiet to help you sleep.", "Try blackout curtains or an eye mask.", NHSS, CL),
 ("Sleep", "Screens and Bedtime", "Try to avoid phones and screens close to bedtime to help your mind wind down.", "Charge your phone outside the bedroom.", NHSS, HT),
 ("Hydration", "Stay Hydrated", "The NHS suggests aiming for about 6 to 8 glasses of fluid a day. Water, lower-fat milk and sugar-free drinks count.", "Keep a bottle in sight.", NHSW, HT),
 ("Hydration", "Water First", "Plain water has no sugar and no calories, making it a simple everyday choice.", "Add lemon or mint for flavour.", NHSW, WR),
 ("Hydration", "Read the Signs", "Pale, clear urine is a sign you are well hydrated; dark urine can mean you need more fluids.", "Drink a glass of water now.", NHSW, DYK),
 ("Hydration", "Drink More When It's Hot", "You may need more fluids in hot weather or when you are being active.", "Sip regularly through the day.", NHSW, HT),
 ("Mental Wellness", "Connect", "Connecting with other people is one of the NHS's five steps to mental wellbeing.", "Message a friend today.", NHSM, ST),
 ("Mental Wellness", "Be Active for Your Mind", "Being active is one of the five steps to mental wellbeing. Find something you enjoy.", "Take a short walk outside.", NHSM, HT),
 ("Mental Wellness", "Keep Learning", "Learning something new is one of the five steps to mental wellbeing.", "Try a new recipe, skill or hobby.", NHSM, HT),
 ("Mental Wellness", "Give to Others", "Small acts of kindness and giving are another of the five steps to mental wellbeing.", "Do one kind thing today.", NHSM, WR),
 ("Mental Wellness", "Notice the Moment", "Paying attention to the present moment, including your thoughts and feelings, is the fifth step to mental wellbeing.", "Take 3 slow breaths.", NHSM, WR),
 ("Mental Wellness", "It's OK to Ask for Help", "If you feel overwhelmed, talking to a GP or someone you trust can help.", "You do not have to cope alone.", NHSM, WR),
 ("Women's Wellness", "Attend Your Screening", "Health screening, such as cervical screening, is offered to eligible people in many countries. Attend when invited.", "Ask your clinic what is available to you.", "https://www.nhs.uk/conditions/cervical-screening/", HT),
 ("Women's Wellness", "Calcium for Bones", "Adults need about 700 mg of calcium a day, found in dairy foods, leafy greens and fortified foods.", "Add a calcium-rich food to breakfast.", "https://www.nhs.uk/conditions/vitamins-and-minerals/calcium/", NF),
 ("Women's Wellness", "Strong Bones Love Movement", "Weight-bearing and resistance exercises help keep bones strong.", "Walk briskly or lift light weights.", "https://www.nhs.uk/conditions/osteoporosis/prevention/", HT),
 ("Women's Wellness", "Iron Matters", "Women aged 19 to 49 need about 14.8 mg of iron a day; sources include beans, lentils, meat and fortified cereals.", "Pair iron-rich foods with vitamin C.", "https://www.nhs.uk/conditions/vitamins-and-minerals/iron/", NF),
 ("Healthy Habits", "Start With One Habit", "Pick one small healthy habit and repeat it daily before adding another.", "Attach it to something you already do.", OWN, ST),
 ("Healthy Habits", "Take a Daily Walk", "Regular walking is a simple way to add moderate physical activity to your day.", "Walk during a phone call.", WHO_PA, CL),
 ("Healthy Habits", "Wash Your Hands", "Washing hands with soap and water helps reduce the spread of infections.", "Wash before eating and after the toilet.", "https://www.who.int/campaigns/world-hand-hygiene-day", HT),
 ("Healthy Habits", "Plan a Healthy Day", "Drink water; eat fruit and veg; move; get outside; sleep well.", "Tick them off as you go.", OWN, CL),
 ("Health Facts", "Heart Health", "WHO reports cardiovascular diseases are the leading cause of death globally.", "Stay active and eat well.", "https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)", DYK),
 ("Health Facts", "Activity Helps Prevention", "Regular physical activity helps prevent and manage heart disease, type 2 diabetes and some cancers.", "Aim to move most days.", WHO_PA, DYK),
 ("Health Facts", "It's Never Too Late to Quit Tobacco", "Quitting tobacco brings health benefits at any age.", "Speak to a health professional about support.", "https://www.who.int/news-room/fact-sheets/detail/tobacco", DYK),
 ("Motivational Quotes", "Progress Over Perfection", "You don't have to be perfect. You just have to keep showing up.", "", OWN, MQ),
 ("Motivational Quotes", "Start Where You Are", "Start where you are. Use what you have. Do what you can.", "", OWN, MQ),
 ("Motivational Quotes", "Small Steps", "Small steps taken every day add up to big changes.", "", OWN, MQ),
 ("Motivational Quotes", "Rest Is Part of It", "Rest is not a reward for finishing. It is part of getting there.", "", OWN, MQ),
 ("Motivational Quotes", "Be Kind to Yourself", "Healthy habits grow best in kindness, not criticism.", "", OWN, MQ),
 ("Motivational Quotes", "One Healthy Choice", "Every healthy choice is a vote for the person you are becoming.", "", OWN, MQ),
]

cols = ["ID", "Category", "Headline", "Hook", "Main content", "Description", "Supporting tip", "Source URL", "Hashtags",
        "Caption", "CTA", "Image style", "Status", "Review note"]
wb = Workbook()
ws = wb.active
ws.title = "Content"
ws.append(cols)
for i, (cat, h, main, tip, src, sty) in enumerate(R, 1):
    ws.append([f"HP{i:03d}", cat, h, "", main, "", tip, src, DEF_TAGS[cat], "", "",
               sty, "Draft", "Verify against source before publishing" if src != OWN else "Original wording"])
for c in ws[1]:
    c.font, c.fill = Font(name="Arial", bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2E7D5B")
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.font, c.alignment = Font(name="Arial", size=10), Alignment(wrap_text=True, vertical="top")
for col, wd in zip("ABCDEFGHIJKLMN", [8, 18, 28, 30, 60, 50, 34, 42, 38, 20, 20, 24, 12, 30]):
    ws.column_dimensions[col].width = wd
ws.freeze_panes = "A2"
dv = DataValidation(type="list", formula1='"Draft,Ready,Published"', allow_blank=False)
dv2 = DataValidation(type="list", formula1='"' + ",".join(TEMPLATES) + '"', allow_blank=True)
ws.add_data_validation(dv); ws.add_data_validation(dv2)
dv.add(f"M2:M500"); dv2.add("L2:L500")
a = wb.create_sheet("About")
for line in ["HealthPost Creator content library",
             "Edit rows in the Content sheet; keep the column headers. Status: Draft / Ready / Published.",
             "Hook (opening line), Description (caption body), Caption, CTA, Hashtags are optional; blank = auto-generated. CTA blank = Follow + Subscribe + Link in bio from Branding.",
             "Myth vs Fact rows: write 'Myth: ... Fact: ...' in Main content.",
             "All facts are paraphrased from the WHO/NHS page in Source URL. Re-verify before posting; wording may change.",
             "General information only - not medical advice or a substitute for a healthcare professional."]:
    a.append([line])
a.column_dimensions["A"].width = 110
wb.save("Health_Content.xlsx")
print("rows:", len(R))
