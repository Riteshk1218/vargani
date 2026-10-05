"""Marathi and Hindi translations for backend messages.

Workflow: `python manage.py makemessages -l mr -l hi`, add new strings here, then
`python locale/translations.py && python manage.py compilemessages`.
User-entered data (names, addresses, organization names) is never translated.
"""

from pathlib import Path

import polib

T = {
    "%(actor)s asked to void receipt %(number)s (₹%(amount)s): %(reason)s": (
        "%(actor)s यांनी पावती %(number)s (₹%(amount)s) रद्द करण्याची विनंती केली: %(reason)s",
        "%(actor)s ने रसीद %(number)s (₹%(amount)s) रद्द करने का अनुरोध किया: %(reason)s",
    ),
    "%(actor)s sent ₹%(amount)s paid to %(payee)s for approval.": (
        "%(actor)s यांनी %(payee)s यांना दिलेले ₹%(amount)s मंजुरीसाठी पाठवले.",
        "%(actor)s ने %(payee)s को दिए गए ₹%(amount)s मंज़ूरी के लिए भेजे।",
    ),
    "Choose a user who has access to this organization.": (
        "या संस्थेत प्रवेश असलेला वापरकर्ता निवडा.",
        "ऐसा उपयोगकर्ता चुनें जिसकी इस संस्था तक पहुँच हो।",
    ),
    "Contribution reminder": ("वर्गणी स्मरणपत्र", "योगदान अनुस्मारक"),
    "Enter your mobile number.": ("तुमचा मोबाइल नंबर टाका.", "अपना मोबाइल नंबर दर्ज करें।"),
    "Expense approved": ("खर्च मंजूर", "खर्च स्वीकृत"),
    "Expense rejected": ("खर्च नाकारला", "खर्च अस्वीकृत"),
    "Expense waiting for approval": ("खर्च मंजुरीच्या प्रतीक्षेत", "खर्च मंज़ूरी की प्रतीक्षा में"),
    "Member": ("सभासद", "सदस्य"),
    "Namaskar %(name)s, ₹%(amount)s is due for %(type)s (%(event)s) to %(organization)s. Thank you.": (
        "नमस्कार %(name)s, %(organization)s कडे %(type)s (%(event)s) साठी ₹%(amount)s बाकी आहे. धन्यवाद.",
        "नमस्कार %(name)s, %(organization)s को %(type)s (%(event)s) के लिए ₹%(amount)s बकाया है। धन्यवाद।",
    ),
    "Online payment": ("ऑनलाइन पेमेंट", "ऑनलाइन भुगतान"),
    "Online payment failed": ("ऑनलाइन पेमेंट अयशस्वी", "ऑनलाइन भुगतान विफल"),
    "Online payment is not available right now. Please try again later or pay your collector.": (
        "ऑनलाइन पेमेंट सध्या उपलब्ध नाही. कृपया नंतर प्रयत्न करा किंवा तुमच्या वसुलीदाराकडे भरा.",
        "ऑनलाइन भुगतान अभी उपलब्ध नहीं है। कृपया बाद में प्रयास करें या अपने संग्रहकर्ता को भुगतान करें।",
    ),
    "Payment not completed": ("पेमेंट पूर्ण झाले नाही", "भुगतान पूरा नहीं हुआ"),
    "Payment not found.": ("पेमेंट सापडले नाही.", "भुगतान नहीं मिला।"),
    "Receipt void requested": ("पावती रद्द करण्याची विनंती", "रसीद रद्द करने का अनुरोध"),
    "Receipt voided": ("पावती रद्द झाली", "रसीद रद्द हुई"),
    "Reminders need a mandatory contribution type with an expected amount.": (
        "स्मरणपत्रांसाठी अपेक्षित रक्कम असलेला अनिवार्य वर्गणी प्रकार लागतो.",
        "अनुस्मारक के लिए अपेक्षित राशि वाला अनिवार्य योगदान प्रकार चाहिए।",
    ),
    "Thank you for your contribution": ("तुमच्या योगदानाबद्दल धन्यवाद", "आपके योगदान के लिए धन्यवाद"),
    "The amount paid does not match the order.": (
        "भरलेली रक्कम ऑर्डरशी जुळत नाही.",
        "भुगतान की गई राशि ऑर्डर से मेल नहीं खाती।",
    ),
    "The member portal is not available for this organization.": (
        "या संस्थेसाठी सभासद पोर्टल उपलब्ध नाही.",
        "इस संस्था के लिए सदस्य पोर्टल उपलब्ध नहीं है।",
    ),
    "The payment could not be verified.": ("पेमेंटची पडताळणी होऊ शकली नाही.", "भुगतान का सत्यापन नहीं हो सका।"),
    "This gateway payment was already used.": ("हे गेटवे पेमेंट आधीच वापरले गेले आहे.", "यह गेटवे भुगतान पहले ही उपयोग हो चुका है।"),
    "This login is already linked to another person here.": (
        "हे लॉगिन येथे आधीच दुसऱ्या व्यक्तीशी जोडलेले आहे.",
        "यह लॉगिन यहाँ पहले से किसी अन्य व्यक्ति से जुड़ा है।",
    ),
    "This payment is no longer waiting for the gateway.": (
        "हे पेमेंट आता गेटवेच्या प्रतीक्षेत नाही.",
        "यह भुगतान अब गेटवे की प्रतीक्षा में नहीं है।",
    ),
    "This person is already linked to another login. Unlink it first.": (
        "ही व्यक्ती आधीच दुसऱ्या लॉगिनशी जोडलेली आहे. आधी ते जोडणी काढा.",
        "यह व्यक्ति पहले से किसी अन्य लॉगिन से जुड़ा है। पहले उसे हटाएँ।",
    ),
    "Void request rejected": ("रद्द करण्याची विनंती नाकारली", "रद्द करने का अनुरोध अस्वीकृत"),
    "Your login is not linked to a member record yet. Please contact your organization.": (
        "तुमचे लॉगिन अद्याप सभासद नोंदीशी जोडलेले नाही. कृपया तुमच्या संस्थेशी संपर्क साधा.",
        "आपका लॉगिन अभी किसी सदस्य रिकॉर्ड से नहीं जुड़ा है। कृपया अपनी संस्था से संपर्क करें।",
    ),
    "Your payment of ₹%(amount)s for %(event)s did not go through. Any money deducted will be returned.": (
        "%(event)s साठी तुमचे ₹%(amount)s चे ऑनलाइन पेमेंट पूर्ण झाले नाही. पैसे कापले गेले असल्यास तुमची बँक ते परत करेल.",
        "%(event)s के लिए आपका ₹%(amount)s का ऑनलाइन भुगतान पूरा नहीं हुआ। यदि पैसे कटे हैं तो आपका बैंक उन्हें लौटा देगा।",
    ),
    "Your request to void receipt %(number)s was approved by %(actor)s.": (
        "पावती %(number)s रद्द करण्याची तुमची विनंती %(actor)s यांनी मंजूर केली.",
        "रसीद %(number)s रद्द करने का आपका अनुरोध %(actor)s ने स्वीकार किया।",
    ),
    "Your request to void receipt %(number)s was rejected by %(actor)s.": (
        "पावती %(number)s रद्द करण्याची तुमची विनंती %(actor)s यांनी नाकारली.",
        "रसीद %(number)s रद्द करने का आपका अनुरोध %(actor)s ने अस्वीकार किया।",
    ),
    "₹%(amount)s is due for %(type)s (%(event)s). Please pay your collector or online.": (
        "%(type)s (%(event)s) साठी ₹%(amount)s बाकी आहे. कृपया वसुलीदाराकडे किंवा ऑनलाइन भरा.",
        "%(type)s (%(event)s) के लिए ₹%(amount)s बकाया है। कृपया संग्रहकर्ता को या ऑनलाइन भुगतान करें।",
    ),
    "₹%(amount)s paid to %(payee)s was approved by %(actor)s.": (
        "%(payee)s यांना दिलेले ₹%(amount)s %(actor)s यांनी मंजूर केले.",
        "%(payee)s को दिए गए ₹%(amount)s %(actor)s ने स्वीकृत किए।",
    ),
    "₹%(amount)s paid to %(payee)s was rejected by %(actor)s: %(reason)s": (
        "%(payee)s यांना दिलेले ₹%(amount)s %(actor)s यांनी नाकारले: %(reason)s",
        "%(payee)s को दिए गए ₹%(amount)s %(actor)s ने अस्वीकार किए: %(reason)s",
    ),
    "₹%(amount)s received for %(event)s. Receipt no. %(number)s.": (
        "%(event)s साठी ₹%(amount)s मिळाले. पावती क्र. %(number)s.",
        "%(event)s के लिए ₹%(amount)s प्राप्त हुए। रसीद क्र. %(number)s।",
    ),
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
    # Phase 3
    "This user cannot collect contributions.": ("हा वापरकर्ता वसुली करू शकत नाही.", "यह उपयोगकर्ता संग्रह नहीं कर सकता।"),
    "Assign at most 500 people at a time.": ("एका वेळी जास्तीत जास्त 500 लोक सोपवा.", "एक बार में अधिकतम 500 लोग सौंपें।"),
    "Only a voided receipt can be corrected.": ("फक्त रद्द पावतीच दुरुस्त करता येते.", "केवल रद्द रसीद ही सुधारी जा सकती है।"),
    "The corrected receipt must be in the same event.": (
        "दुरुस्त करायची पावती त्याच कार्यक्रमातील असावी.",
        "सुधारी जाने वाली रसीद उसी कार्यक्रम की होनी चाहिए।",
    ),
    "This receipt has already been corrected.": ("ही पावती आधीच दुरुस्त केली आहे.", "यह रसीद पहले ही सुधारी जा चुकी है।"),
    "A correction must be a received payment.": ("दुरुस्ती ही मिळालेले पेमेंट असावी.", "सुधार प्राप्त भुगतान होना चाहिए।"),
    "This person is not assigned to you for this event.": (
        "ही व्यक्ती या कार्यक्रमासाठी तुम्हाला सोपवलेली नाही.",
        "यह व्यक्ति इस कार्यक्रम के लिए आपको सौंपा नहीं गया है।",
    ),
    "Namaskar %(name)s, thank you for your contribution of Rs %(amount)s to %(organization)s (%(event)s). "
    "Receipt no. %(number)s: %(url)s": (
        "नमस्कार %(name)s, %(organization)s (%(event)s) साठी तुमच्या ₹%(amount)s योगदानाबद्दल धन्यवाद. "
        "पावती क्र. %(number)s: %(url)s",
        "नमस्कार %(name)s, %(organization)s (%(event)s) के लिए आपके ₹%(amount)s योगदान के लिए धन्यवाद। "
        "रसीद क्र. %(number)s: %(url)s",
    ),
    "VOID": ("रद्द", "रद्द"),
    "Reg. no.": ("नोंदणी क्र.", "पंजीकरण क्र."),
    "Receipt": ("पावती", "रसीद"),
    "Receipt no.": ("पावती क्र.", "रसीद क्र."),
    "Financial year %(label)s": ("आर्थिक वर्ष %(label)s", "वित्तीय वर्ष %(label)s"),
    "Received from": ("यांच्याकडून मिळाले", "से प्राप्त"),
    "Mobile": ("मोबाइल", "मोबाइल"),
    "Address": ("पत्ता", "पता"),
    "Details": ("तपशील", "विवरण"),
    "Amount": ("रक्कम", "राशि"),
    "Total": ("एकूण", "कुल"),
    "Payment mode": ("पेमेंट पद्धत", "भुगतान का तरीका"),
    "Collected by": ("वसूल करणारे", "संग्रहकर्ता"),
    "Void reason": ("रद्द करण्याचे कारण", "रद्द करने का कारण"),
    "Thank you for your contribution.": ("तुमच्या योगदानाबद्दल धन्यवाद.", "आपके योगदान के लिए धन्यवाद।"),
    "Authorised signatory": ("अधिकृत स्वाक्षरी", "अधिकृत हस्ताक्षरकर्ता"),
    "Give a reason for voiding this receipt.": ("ही पावती रद्द करण्याचे कारण द्या.", "यह रसीद रद्द करने का कारण दें।"),
    "This receipt is already void.": ("ही पावती आधीच रद्द आहे.", "यह रसीद पहले से रद्द है।"),
    "A void request for this receipt is already waiting for approval.": (
        "या पावतीची रद्द विनंती आधीच मंजुरीच्या प्रतीक्षेत आहे.",
        "इस रसीद का रद्द अनुरोध पहले से स्वीकृति की प्रतीक्षा में है।",
    ),
    "Someone other than the requester must approve this.": (
        "विनंती करणाऱ्याशिवाय दुसऱ्या व्यक्तीने हे मंजूर करावे.",
        "अनुरोध करने वाले के अलावा किसी और को इसे स्वीकृत करना होगा।",
    ),
    "Cash": ("रोख", "नकद"),
    "UPI": ("UPI", "UPI"),
    "Bank transfer": ("बँक ट्रान्सफर", "बैंक ट्रांसफर"),
    "Cheque": ("धनादेश", "चेक"),
    "Online": ("ऑनलाइन", "ऑनलाइन"),
    "Other": ("इतर", "अन्य"),
    # Phase 4
    "A category with this name already exists.": ("या नावाचा प्रकार आधीच आहे.", "इस नाम की श्रेणी पहले से है।"),
    "Action": ("कृती", "कार्रवाई"),
    "Active": ("सक्रिय", "सक्रिय"),
    "All events": ("सर्व कार्यक्रम", "सभी कार्यक्रम"),
    "An expense can have at most 10 attachments.": (
        "एका खर्चाला जास्तीत जास्त 10 बिले जोडता येतात.",
        "एक खर्च में अधिकतम 10 बिल जोड़े जा सकते हैं।",
    ),
    "Approved": ("मंजूर", "स्वीकृत"),
    "Approved by": ("मंजूर करणारे", "स्वीकृत करने वाले"),
    "Archived": ("संग्रहित", "संग्रहित"),
    "Area": ("परिसर", "क्षेत्र"),
    "Audit log": ("बदलांची नोंद", "ऑडिट लॉग"),
    "Balance": ("शिल्लक", "शेष"),
    "Bank interest": ("बँक व्याज", "बैंक ब्याज"),
    "Building": ("इमारत", "भवन"),
    "Category": ("प्रकार", "श्रेणी"),
    "Changed fields": ("बदललेली माहिती", "बदले गए फ़ील्ड"),
    "Choose a file.": ("फाइल निवडा.", "फ़ाइल चुनें।"),
    "City": ("शहर", "शहर"),
    "Closed": ("बंद", "बंद"),
    "Code": ("कोड", "कोड"),
    "Collector": ("वसुलीदार", "संग्रहकर्ता"),
    "Collector-wise collection": ("वसुलीदारानुसार वसुली", "संग्रहकर्ता के अनुसार संग्रह"),
    "Contribution type": ("वर्गणी प्रकार", "योगदान प्रकार"),
    "Contributions": ("वर्गणी", "योगदान"),
    "Contributors": ("देणगीदार", "योगदानकर्ता"),
    "Date": ("तारीख", "तारीख"),
    "Description": ("वर्णन", "विवरण"),
    "Donation box": ("दानपेटी", "दान पेटी"),
    "Draft": ("मसुदा", "ड्राफ्ट"),
    "Due": ("बाकी", "बकाया"),
    "Email": ("ईमेल", "ईमेल"),
    "Ends": ("शेवट", "समाप्ति"),
    "Enter who was paid.": ("कोणाला पैसे दिले ते लिहा.", "किसे भुगतान किया, वह लिखें।"),
    "Event": ("कार्यक्रम", "कार्यक्रम"),
    "Event not found.": ("कार्यक्रम सापडला नाही.", "कार्यक्रम नहीं मिला।"),
    "Event-wise balance": ("कार्यक्रमानुसार शिल्लक", "कार्यक्रम के अनुसार शेष"),
    "Events": ("कार्यक्रम", "कार्यक्रम"),
    "Expected": ("अपेक्षित", "अपेक्षित"),
    "Expense": ("खर्च", "खर्च"),
    "Expenses": ("खर्च", "खर्च"),
    "Financial year not found.": ("आर्थिक वर्ष सापडले नाही.", "वित्तीय वर्ष नहीं मिला।"),
    "Flat / house": ("सदनिका / घर", "फ्लैट / मकान"),
    "For month": ("महिना", "महीना"),
    "Fund": ("निधी", "निधि"),
    "Fund-wise collection": ("निधीनुसार वसुली", "निधि के अनुसार संग्रह"),
    "Generated on %(when)s": ("%(when)s रोजी तयार", "%(when)s को बनाया गया"),
    "Give a reason.": ("कारण द्या.", "कारण बताएं।"),
    "Head": ("बाब", "मद"),
    "IP address": ("IP पत्ता", "IP पता"),
    "Inactive": ("निष्क्रिय", "निष्क्रिय"),
    "Income": ("उत्पन्न", "आय"),
    "Income and expenditure": ("जमा-खर्च", "आय-व्यय"),
    "Income counts confirmed contributions and recorded other income. Expenses count approved expenses.": (
        "उत्पन्नात निश्चित वर्गणी आणि नोंदवलेले इतर उत्पन्न धरले आहे. खर्चात फक्त मंजूर खर्च धरला आहे.",
        "आय में पुष्ट योगदान और दर्ज अन्य आय गिनी गई है। खर्च में केवल स्वीकृत खर्च गिना गया है।",
    ),
    "Issued": ("दिलेली", "जारी"),
    "Month": ("महिना", "महीना"),
    "Monthly collection": ("मासिक वसुली", "मासिक संग्रह"),
    "Name": ("नाव", "नाम"),
    "No fund": ("निधी नाही", "कोई निधि नहीं"),
    "No records for these filters.": ("या निवडीसाठी नोंदी नाहीत.", "इन फ़िल्टर के लिए कोई रिकॉर्ड नहीं।"),
    "Office (no collector)": ("कार्यालय (वसुलीदार नाही)", "कार्यालय (कोई संग्रहकर्ता नहीं)"),
    "Only an approver can void an approved expense.": (
        "मंजूर खर्च फक्त मंजुरी देणारेच रद्द करू शकतात.",
        "स्वीकृत खर्च केवल स्वीकृति देने वाले ही रद्द कर सकते हैं।",
    ),
    "Only mandatory contribution types with an expected amount are included.": (
        "फक्त अपेक्षित रक्कम असलेले अनिवार्य वर्गणी प्रकार धरले आहेत.",
        "केवल अपेक्षित राशि वाले अनिवार्य योगदान प्रकार शामिल हैं।",
    ),
    "Only the first %(n)s rows are shown. Use Excel or CSV for the full list.": (
        "फक्त पहिल्या %(n)s ओळी दाखवल्या आहेत. पूर्ण यादीसाठी Excel किंवा CSV वापरा.",
        "केवल पहली %(n)s पंक्तियां दिखाई गई हैं। पूरी सूची के लिए Excel या CSV का उपयोग करें।",
    ),
    "Other income": ("इतर उत्पन्न", "अन्य आय"),
    "Paid": ("भरले", "भुगतान किया"),
    "Paid to": ("कोणाला दिले", "किसे दिया"),
    "Participants": ("सहभागी", "प्रतिभागी"),
    "Payment mode summary": ("पेमेंट पद्धतीनुसार सारांश", "भुगतान तरीके का सारांश"),
    "Payments": ("पेमेंट्स", "भुगतान"),
    "Pending dues": ("बाकी वर्गणी", "बकाया योगदान"),
    "People": ("लोक", "लोग"),
    "Receipt register": ("पावती नोंदवही", "रसीद रजिस्टर"),
    "Record id": ("नोंद क्र.", "रिकॉर्ड आईडी"),
    "Record type": ("नोंदीचा प्रकार", "रिकॉर्ड प्रकार"),
    "Recorded": ("नोंदवले", "दर्ज"),
    "Reference": ("संदर्भ", "संदर्भ"),
    "Rejected": ("नामंजूर", "अस्वीकृत"),
    "Role": ("भूमिका", "भूमिका"),
    "Rows": ("ओळी", "पंक्तियां"),
    "Sales": ("विक्री", "बिक्री"),
    "Select an event.": ("कार्यक्रम निवडा.", "कार्यक्रम चुनें।"),
    "Source": ("स्रोत", "स्रोत"),
    "Sponsorship": ("प्रायोजकत्व", "प्रायोजन"),
    "Starts": ("सुरुवात", "आरंभ"),
    "Status": ("स्थिती", "स्थिति"),
    "Submitted": ("मंजुरीसाठी पाठवले", "स्वीकृति के लिए भेजा"),
    "System": ("प्रणाली", "सिस्टम"),
    "Target": ("लक्ष्य", "लक्ष्य"),
    "The date cannot be in the future.": ("तारीख भविष्यातील असू शकत नाही.", "तारीख भविष्य की नहीं हो सकती।"),
    "The end date must be after the start date.": ("शेवटची तारीख सुरुवातीनंतर असावी.", "अंतिम तारीख आरंभ के बाद होनी चाहिए।"),
    "The total counts issued receipts only; void receipts are listed but not added.": (
        "एकूण रकमेत फक्त दिलेल्या पावत्या धरल्या आहेत; रद्द पावत्या यादीत आहेत पण बेरजेत नाहीत.",
        "कुल में केवल जारी रसीदें गिनी गई हैं; रद्द रसीदें सूची में हैं पर जोड़ी नहीं गईं।",
    ),
    "This event is closed. Money records cannot be added or changed.": (
        "हा कार्यक्रम बंद आहे. पैशांच्या नोंदी जोडता किंवा बदलता येणार नाहीत.",
        "यह कार्यक्रम बंद है। पैसों के रिकॉर्ड जोड़े या बदले नहीं जा सकते।",
    ),
    "Time": ("वेळ", "समय"),
    "Total: %(label)s": ("एकूण: %(label)s", "कुल: %(label)s"),
    "Type": ("प्रकार", "प्रकार"),
    "Upload a JPG, PNG or WEBP image, or a PDF.": (
        "JPG, PNG किंवा WEBP फोटो, किंवा PDF अपलोड करा.",
        "JPG, PNG या WEBP फोटो, या PDF अपलोड करें।",
    ),
    "User": ("वापरकर्ता", "उपयोगकर्ता"),
    "Void": ("रद्द", "रद्द"),
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
