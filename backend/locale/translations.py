"""Marathi and Hindi translations for backend messages.

Workflow: `python manage.py makemessages -l mr -l hi`, add new strings here, then
`python locale/translations.py && python manage.py compilemessages`.
User-entered data (names, addresses, organization names) is never translated.
"""

from pathlib import Path

import polib

T = {
    "Please wait before requesting another code.": (
        "दुसरा कोड मागण्यापूर्वी कृपया थोडा वेळ थांबा.",
        "दूसरा कोड मांगने से पहले कृपया थोड़ा इंतज़ार करें।",
    ),
    "Too many codes requested. Try again later.": (
        "खूप वेळा कोड मागितला आहे. थोड्या वेळाने पुन्हा प्रयत्न करा.",
        "बहुत बार कोड मांगा गया है। कुछ देर बाद फिर से प्रयास करें।",
    ),
    "Your verification code": ("तुमचा पडताळणी कोड", "आपका सत्यापन कोड"),
    "Your verification code is %(code)s. It expires in %(minutes)s minutes. Do not share it.": (
        "तुमचा पडताळणी कोड %(code)s आहे. तो %(minutes)s मिनिटांत संपेल. तो कोणालाही सांगू नका.",
        "आपका सत्यापन कोड %(code)s है। यह %(minutes)s मिनट में समाप्त हो जाएगा। इसे किसी के साथ साझा न करें।",
    ),
    "The code is invalid or has expired.": (
        "कोड चुकीचा आहे किंवा त्याची मुदत संपली आहे.",
        "कोड गलत है या उसकी समय-सीमा समाप्त हो गई है।",
    ),
    "Enter an email address or a mobile number.": ("ईमेल पत्ता किंवा मोबाइल नंबर टाका.", "ईमेल पता या मोबाइल नंबर दर्ज करें।"),
    "An account with these details already exists. Please log in.": (
        "या तपशिलांसह खाते आधीच अस्तित्वात आहे. कृपया लॉग इन करा.",
        "इन विवरणों के साथ खाता पहले से मौजूद है। कृपया लॉग इन करें।",
    ),
    "Please verify your account before logging in.": (
        "लॉग इन करण्यापूर्वी कृपया तुमचे खाते पडताळा.",
        "लॉग इन करने से पहले कृपया अपना खाता सत्यापित करें।",
    ),
    "Invalid login details.": ("लॉग इन तपशील चुकीचे आहेत.", "लॉग इन विवरण गलत हैं।"),
    "Refresh token required.": ("रिफ्रेश टोकन आवश्यक आहे.", "रिफ्रेश टोकन आवश्यक है।"),
    "If an account exists, a reset code has been sent.": (
        "खाते अस्तित्वात असल्यास, रीसेट कोड पाठवला आहे.",
        "यदि खाता मौजूद है, तो रीसेट कोड भेज दिया गया है।",
    ),
    "Your password has been reset. Please log in.": (
        "तुमचा पासवर्ड रीसेट झाला आहे. कृपया लॉग इन करा.",
        "आपका पासवर्ड रीसेट हो गया है। कृपया लॉग इन करें।",
    ),
    "Your current password is incorrect.": ("तुमचा सध्याचा पासवर्ड चुकीचा आहे.", "आपका वर्तमान पासवर्ड गलत है।"),
    "Select an organization (X-Organization-ID header).": ("संस्था निवडा.", "संस्था चुनें।"),
    "You are not a member of this organization.": ("तुम्ही या संस्थेचे सदस्य नाही.", "आप इस संस्था के सदस्य नहीं हैं।"),
    "Select an event (event parameter).": ("कार्यक्रम निवडा.", "कार्यक्रम चुनें।"),
    "This conflicts with existing data.": ("हे आधीच्या माहितीशी जुळत नाही.", "यह मौजूदा जानकारी से टकराता है।"),
    "This action is not allowed in the record's current state.": (
        "सध्याच्या स्थितीत ही क्रिया करता येणार नाही.",
        "वर्तमान स्थिति में यह क्रिया नहीं की जा सकती।",
    ),
    "This request breaks a business rule.": (
        "ही विनंती नियमांनुसार करता येणार नाही.",
        "यह अनुरोध नियमों के अनुसार नहीं किया जा सकता।",
    ),
    "Some fields are invalid.": ("काही माहिती चुकीची आहे.", "कुछ जानकारी गलत है।"),
    "Not found.": ("सापडले नाही.", "नहीं मिला।"),
    "Something went wrong. Please try again.": (
        "काहीतरी चुकले. कृपया पुन्हा प्रयत्न करा.",
        "कुछ गलत हो गया। कृपया फिर से प्रयास करें।",
    ),
    "Enter a valid mobile number.": ("योग्य मोबाइल नंबर टाका.", "सही मोबाइल नंबर दर्ज करें।"),
    "Enter the event name.": ("कार्यक्रमाचे नाव टाका.", "कार्यक्रम का नाम दर्ज करें।"),
    "Use only letters and numbers.": ("फक्त अक्षरे आणि अंक वापरा.", "केवल अक्षर और अंक इस्तेमाल करें।"),
    "Unknown module or invalid value.": ("अज्ञात विभाग किंवा चुकीचे मूल्य.", "अज्ञात मॉड्यूल या गलत मान।"),
    "An event cannot move to another financial year.": (
        "कार्यक्रम दुसऱ्या आर्थिक वर्षात हलवता येत नाही.",
        "कार्यक्रम को दूसरे वित्तीय वर्ष में नहीं ले जाया जा सकता।",
    ),
    "This financial year is closed.": ("हे आर्थिक वर्ष बंद आहे.", "यह वित्तीय वर्ष बंद है।"),
    "End date must be on or after the start date.": (
        "शेवटची तारीख सुरुवातीच्या तारखेनंतर किंवा त्याच दिवशी हवी.",
        "समाप्ति तिथि आरंभ तिथि के बाद या उसी दिन होनी चाहिए।",
    ),
    "Another event in this financial year uses this code.": (
        "या आर्थिक वर्षातील दुसरा कार्यक्रम हा कोड वापरतो.",
        "इस वित्तीय वर्ष का दूसरा कार्यक्रम यह कोड इस्तेमाल करता है।",
    ),
    "This cannot be changed.": ("हे बदलता येत नाही.", "इसे बदला नहीं जा सकता।"),
    "This person is already part of the event.": ("ही व्यक्ती आधीच कार्यक्रमात आहे.", "यह व्यक्ति पहले से कार्यक्रम में है।"),
    "Festival": ("उत्सव", "उत्सव"),
    "Festivals such as Ganesh Chaturthi, Navratri or Dahi Handi.": (
        "गणेश चतुर्थी, नवरात्री किंवा दहीहंडी यांसारखे उत्सव.",
        "गणेश चतुर्थी, नवरात्रि या दही हांडी जैसे उत्सव।",
    ),
    "Fundraising": ("निधी संकलन", "धन संग्रह"),
    "A campaign that collects donations towards a goal.": (
        "ठराविक उद्दिष्टासाठी देणगी गोळा करणारी मोहीम.",
        "किसी लक्ष्य के लिए दान इकट्ठा करने का अभियान।",
    ),
    "Membership": ("सभासदत्व", "सदस्यता"),
    "Annual or monthly membership and Vargani collection.": (
        "वार्षिक किंवा मासिक सभासदत्व आणि वर्गणी संकलन.",
        "वार्षिक या मासिक सदस्यता और वर्गणी संग्रह।",
    ),
    "Society": ("सोसायटी", "सोसाइटी"),
    "Housing society maintenance, funds and expenses.": (
        "गृहनिर्माण सोसायटीची देखभाल, निधी आणि खर्च.",
        "हाउसिंग सोसाइटी का रखरखाव, निधि और खर्च।",
    ),
    "Custom": ("सानुकूल", "कस्टम"),
    "Start empty and choose the modules yourself.": (
        "रिकाम्यापासून सुरू करा आणि विभाग स्वतः निवडा.",
        "खाली से शुरू करें और मॉड्यूल खुद चुनें।",
    ),
    "Enter the organization name.": ("संस्थेचे नाव टाका.", "संस्था का नाम दर्ज करें।"),
    "End date must be after the start date.": (
        "शेवटची तारीख सुरुवातीच्या तारखेनंतर हवी.",
        "समाप्ति तिथि आरंभ तिथि के बाद होनी चाहिए।",
    ),
    "A closed financial year cannot be edited.": ("बंद आर्थिक वर्ष बदलता येत नाही.", "बंद वित्तीय वर्ष को बदला नहीं जा सकता।"),
    "A financial year with this label already exists.": (
        "या नावाचे आर्थिक वर्ष आधीच आहे.",
        "इस नाम का वित्तीय वर्ष पहले से मौजूद है।",
    ),
    "This financial year overlaps another financial year.": (
        "हे आर्थिक वर्ष दुसऱ्या आर्थिक वर्षाशी जुळते.",
        "यह वित्तीय वर्ष दूसरे वित्तीय वर्ष से टकराता है।",
    ),
    "Unknown setting.": ("अज्ञात सेटिंग.", "अज्ञात सेटिंग।"),
    "Invalid value.": ("चुकीचे मूल्य.", "गलत मान।"),
    "Upload a PNG, JPG, JPEG or WEBP image.": (
        "PNG, JPG, JPEG किंवा WEBP प्रतिमा अपलोड करा.",
        "PNG, JPG, JPEG या WEBP छवि अपलोड करें।",
    ),
    "The file is too large.": ("फाइल खूप मोठी आहे.", "फ़ाइल बहुत बड़ी है।"),
    "The image is too small. Use at least 512 × 512 pixels.": (
        "प्रतिमा खूप लहान आहे. किमान 512 × 512 पिक्सेल वापरा.",
        "छवि बहुत छोटी है। कम से कम 512 × 512 पिक्सेल इस्तेमाल करें।",
    ),
    "A closed financial year cannot be made current.": (
        "बंद आर्थिक वर्ष चालू करता येत नाही.",
        "बंद वित्तीय वर्ष को चालू नहीं किया जा सकता।",
    ),
    "This person already has access to the organization.": (
        "या व्यक्तीला संस्थेत आधीच प्रवेश आहे.",
        "इस व्यक्ति को संस्था में पहले से पहुँच है।",
    ),
    "You have been invited to join %(org)s as %(role)s. Open this link to accept: %(link)s": (
        "तुम्हाला %(org)s मध्ये %(role)s म्हणून सामील होण्याचे निमंत्रण आहे. स्वीकारण्यासाठी ही लिंक उघडा: %(link)s",
        "आपको %(org)s में %(role)s के रूप में जुड़ने का निमंत्रण है। स्वीकार करने के लिए यह लिंक खोलें: %(link)s",
    ),
    "Invitation to %(org)s": ("%(org)s कडून निमंत्रण", "%(org)s से निमंत्रण"),
    "This invitation is invalid or has expired.": (
        "हे निमंत्रण अवैध आहे किंवा त्याची मुदत संपली आहे.",
        "यह निमंत्रण अमान्य है या उसकी समय-सीमा समाप्त हो गई है।",
    ),
    "This invitation was sent to a different email or mobile number.": (
        "हे निमंत्रण दुसऱ्या ईमेल किंवा मोबाइल नंबरवर पाठवले होते.",
        "यह निमंत्रण किसी दूसरे ईमेल या मोबाइल नंबर पर भेजा गया था।",
    ),
    "You already have access to this organization.": ("तुम्हाला या संस्थेत आधीच प्रवेश आहे.", "आपको इस संस्था में पहले से पहुँच है।"),
    "The organization must keep at least one active Organization Admin.": (
        "संस्थेत किमान एक सक्रिय संस्था प्रशासक असणे आवश्यक आहे.",
        "संस्था में कम से कम एक सक्रिय संस्था एडमिन होना ज़रूरी है।",
    ),
    "Enter the person's name.": ("व्यक्तीचे नाव टाका.", "व्यक्ति का नाम दर्ज करें।"),
    "A new payment must be successful or pending.": (
        "नवीन पेमेंट यशस्वी किंवा प्रलंबित असणे आवश्यक आहे.",
        "नया भुगतान सफल या लंबित होना चाहिए।",
    ),
    "Add at least one contribution.": ("किमान एक वर्गणी जोडा.", "कम से कम एक योगदान जोड़ें।"),
    "Amount must be more than zero.": ("रक्कम शून्यापेक्षा जास्त असावी.", "राशि शून्य से अधिक होनी चाहिए।"),
    "Amount must equal the total of the contribution lines.": (
        "रक्कम सर्व वर्गणीच्या एकूण रकमेइतकी असावी.",
        "राशि सभी योगदानों के कुल के बराबर होनी चाहिए।",
    ),
    "Dues are tracked only for mandatory contribution types.": (
        "थकबाकी फक्त अनिवार्य वर्गणी प्रकारांसाठी मोजली जाते.",
        "बकाया केवल अनिवार्य योगदान प्रकारों के लिए गिना जाता है।",
    ),
    "Enter a name.": ("नाव टाका.", "नाम दर्ज करें।"),
    "Enter the amount expected from each person.": (
        "प्रत्येक व्यक्तीकडून अपेक्षित रक्कम टाका.",
        "हर व्यक्ति से अपेक्षित राशि दर्ज करें।",
    ),
    "Enter the cheque or transaction number.": (
        "चेक किंवा व्यवहार क्रमांक टाका.",
        "चेक या लेन-देन नंबर दर्ज करें।",
    ),
    "Maximum must be at least the minimum.": (
        "कमाल रक्कम किमान रकमेपेक्षा कमी असू शकत नाही.",
        "अधिकतम राशि न्यूनतम से कम नहीं हो सकती।",
    ),
    "Payment date cannot be in the future.": (
        "पेमेंटची तारीख भविष्यातील असू शकत नाही.",
        "भुगतान की तारीख भविष्य की नहीं हो सकती।",
    ),
    "Select the month this contribution is for.": (
        "ही वर्गणी कोणत्या महिन्याची आहे ते निवडा.",
        "यह योगदान किस महीने का है, चुनें।",
    ),
    "This cannot be changed after collections exist.": (
        "वसुली झाल्यानंतर हे बदलता येत नाही.",
        "संग्रह होने के बाद इसे बदला नहीं जा सकता।",
    ),
    "This contribution type belongs to another event.": (
        "हा वर्गणी प्रकार दुसऱ्या कार्यक्रमाचा आहे.",
        "यह योगदान प्रकार किसी दूसरे कार्यक्रम का है।",
    ),
    "This contribution type is archived.": ("हा वर्गणी प्रकार संग्रहित केला आहे.", "यह योगदान प्रकार संग्रहित है।"),
    "This event already has a contribution type with this name.": (
        "या कार्यक्रमात या नावाचा वर्गणी प्रकार आधीच आहे.",
        "इस कार्यक्रम में इस नाम का योगदान प्रकार पहले से है।",
    ),
    "This event already has a fund with this name.": (
        "या कार्यक्रमात या नावाचा निधी आधीच आहे.",
        "इस कार्यक्रम में इस नाम का फंड पहले से है।",
    ),
    "This event is not active. New collections are not allowed.": (
        "हा कार्यक्रम सक्रिय नाही. नवीन वसुली करता येणार नाही.",
        "यह कार्यक्रम सक्रिय नहीं है। नया संग्रह नहीं किया जा सकता।",
    ),
    "This fund belongs to another event.": ("हा निधी दुसऱ्या कार्यक्रमाचा आहे.", "यह फंड किसी दूसरे कार्यक्रम का है।"),
    "This payment mode cannot be recorded manually.": (
        "ही पेमेंट पद्धत हाताने नोंदवता येत नाही.",
        "यह भुगतान माध्यम हाथ से दर्ज नहीं किया जा सकता।",
    ),
    "This person is archived.": ("ही व्यक्ती संग्रहित केली आहे.", "यह व्यक्ति संग्रहित है।"),
    "Your organization has not allowed collecting from unassigned people.": (
        "तुमच्या संस्थेने न सोपवलेल्या व्यक्तींकडून वसुलीची परवानगी दिलेली नाही.",
        "आपकी संस्था ने बिना सौंपे गए लोगों से संग्रह की अनुमति नहीं दी है।",
    ),
    "English": ("English", "English"),
}


def main():
    root = Path(__file__).resolve().parent
    missing = set()
    for index, lang in enumerate(("mr", "hi")):
        path = root / lang / "LC_MESSAGES" / "django.po"
        po = polib.pofile(str(path))
        for entry in po:
            if entry.msgid in T:
                entry.msgstr = T[entry.msgid][index]
                if "fuzzy" in entry.flags:
                    entry.flags.remove("fuzzy")
            else:
                missing.add(entry.msgid)
        po.metadata["Content-Type"] = "text/plain; charset=UTF-8"
        po.metadata["Language"] = lang
        po.save()
    if missing:
        print("Untranslated:", *sorted(missing), sep="\n  ")


if __name__ == "__main__":
    main()
