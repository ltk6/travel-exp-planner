"""
maps/context.py
===============
Maps structural and situational context signals into normalized English
travel intent keywords for BGE-M3 embedding.

CONTEXT represents the external world: physical environment, visual scene,
weather conditions, place types, scenery, and situational grounding.

Does NOT include: emotional states, user desires/needs, or structured activity labels.

─────────────────────────────────────────────────────────────
SECTION INDEX
─────────────────────────────────────────────────────────────
  A. SEASON & WEATHER        — summer, winter, rain, sunny, holiday
  B. SOCIAL GROUP            — solo, couple, family, friends, corporate
  C. TRIP DURATION           — day trip, weekend, one week, overnight
  D. TRIP DISTANCE           — nearby, domestic, international, remote
  E. BUDGET LEVEL            — budget, affordable, luxury, mid-range
  F. PACE & STYLE            — leisurely, flexible, slow travel, packed
  G. NATURE & LANDSCAPE      — mountain, beach, forest, sunset, lake
  H. TRAVEL INTENT           — vacation, explore, discover, sightseeing
  I. MOOD & ATMOSPHERE       — quiet, lively, romantic, wild, cozy
  J. ACTIVITIES              — swimming, trekking, camping, yoga
  K. FOOD & DRINK            — local food, street food, seafood, coffee
  L. ACCOMMODATION           — hotel, resort, homestay, villa, ecolodge
  M. CULTURAL & HERITAGE     — history, architecture, temple, festival
  N. WELLNESS & HEALTH       — retreat, healing, detox, massage, spa
  O. PHOTOGRAPHY & CONTENT   — instagram, sunset, landscape, drone

IMPLEMENTATION NOTES
──────────────────────────────────────────────────────────────
  • Longer phrases take priority over shorter overlapping ones via
    _dedupe_substrings in registry.py (longest match wins).
  • Context values map external variables that define the physical trip.
  • Vietnamese and English keys are both first-class entries.
──────────────────────────────────────────────────────────────
"""

# ═════════════════════════════════════════════════════════════
# A. SEASON & WEATHER
# ═════════════════════════════════════════════════════════════
SEASON_WEATHER: dict[str, str] = {
    # ── Vietnamese — seasons ────────────────────────────────
    "mùa hè":               "hot sunny months with long daylight hours and conditions favorable for beaches, coastal water, and open outdoor environments at their peak",
    "mùa đông":             "cold months with reduced daylight, low temperatures, and landscapes defined by mist, frost, bare mountain terrain, and highland stillness",
    "mùa xuân":             "transitional season when temperatures rise gently, flowers bloom across hillsides, and natural landscapes shift from dormant to lush and green",
    "mùa thu":              "cooling season marked by changing leaf colors across mountain and highland terrain, golden-lit scenery, and crisp open-air visibility",
    "mùa khô":              "dry season with minimal rainfall, clear skies, and unobstructed access to coastal, outdoor, and open-air environments",
    "mùa mưa":              "wet season with frequent rainfall, dramatically elevated waterfalls, dense saturated greenery, and atmospheric low-visibility forest landscapes",
    "lễ hội":               "festive period when public spaces are visually transformed with lights, decorations, crowds, and culturally animated street environments",
    "dịp lễ hội":           "specific festive occasion with decorated public spaces, traditional performances, and heightened cultural activity in towns and villages",

    # ── Vietnamese — weather ────────────────────────────────
    "nắng":                 "clear sunny conditions with strong direct light illuminating open landscapes, beaches, and outdoor viewpoints",
    "trời nắng đẹp":        "ideal sunny weather with sharp visibility, warm golden light, and photogenic conditions across natural and coastal scenes",
    "mưa":                  "rainfall creating wet reflective surfaces, swollen waterfalls, lush saturated vegetation, and grey overcast atmospheric skies",
    "nóng":                 "high ambient temperature with intense heat shaping exposed outdoor environments, beaches, and open coastal terrain",
    "lạnh":                 "low temperature environment with chilled air defining the character of mountain passes, highland plateaus, and still winter landscapes",
    "hanh":                 "dry cool northern air producing clear skies and crisp visibility across open plains and highland terrain",
    "oi bức":               "oppressive humid heat with dense moisture in the air, typical of lowland and coastal environments in peak summer",
    "sương mù":             "fog and mist reducing visibility and creating an ethereal atmospheric quality over highland valleys and mountain terrain",
    "gió":                  "windy open conditions with moving air across coastal headlands, highland ridges, and exposed outdoor environments",
    "tuyết":                "snow-covered terrain with white-coated mountain landscapes, frozen ground, and rare cold-weather highland scenery in Vietnam",
    "mát mẻ":               "comfortably cool air temperature typical of highland and forested environments, distinct from lowland heat",
    "thời tiết đẹp":        "optimal outdoor conditions with pleasant temperature, good visibility, and favorable light for open-air environments",
    "dễ chịu":              "mild and comfortable ambient conditions without extreme heat, cold, wind, or rain",

    # ── Vietnamese — timing / occasion ─────────────────────
    "cuối tuần":            "two-day break period when short-distance destinations and nearby outdoor environments see increased visitor activity",
    "nghỉ hè":              "extended summer holiday period when beaches, coastal resorts, and outdoor leisure destinations are at peak demand",
    "nghỉ lễ":              "public holiday period characterized by increased travel activity and festive atmosphere at popular destinations",
    "cuối năm":             "year-end period with festive decorations, cooler temperatures in the north, and culturally active urban environments",
    "tết":                  "Vietnamese lunar new year period defined by flower markets, decorated streets, temple crowds, and traditional village atmospheres",
    "tết nguyên đán":       "peak Vietnamese cultural festival period when ancestral villages, pagodas, and old towns are at their most traditionally animated",
    "dịp đặc biệt":         "a marked occasion that transforms the character of a destination beyond its everyday appearance",
    "ngày nghỉ":            "a single day off that opens access to nearby leisure destinations and day-trip environments",

    # ── English — seasons ───────────────────────────────────
    "summer":               "hot sunny season with long days, warm ocean water, and peak conditions for beaches and open coastal environments",
    "winter":               "cold season with low temperatures, short days, and landscapes defined by mist, frost, and highland stillness",
    "spring":               "mild transitional season with blooming flowers, fresh green vegetation, and gradually warming outdoor environments",
    "autumn":               "cooling season with golden foliage, crisp air, and scenic color changes across highland and mountain landscapes",
    "fall":                 "cooling season with golden foliage, crisp air, and scenic color changes across highland and mountain landscapes",
    "monsoon":              "heavy rainfall season producing dramatically lush green terrain, swollen rivers, and atmospheric misty forest environments",
    "rainy season":         "prolonged wet period with frequent rain, elevated waterfalls, dense green growth, and low-visibility atmospheric landscapes",
    "dry season":           "rain-free period with clear skies, low humidity, and optimal access to coastal beaches and open outdoor terrain",

    # ── English — weather ───────────────────────────────────
    "hot weather":          "high ambient temperature shaping the physical character of exposed outdoor environments and coastal landscapes",
    "cold weather":         "low temperature conditions defining the feel of highland terrain, mountain passes, and still winter landscapes",
    "sunny":                "unobstructed sunlight across open terrain producing strong shadows, vivid colors, and clear photographic conditions",
    "foggy":                "dense fog reducing visibility and creating layered atmospheric depth over highland valleys and coastal cliffs",
    "cool weather":         "comfortably below-average temperatures typical of highland forests, elevated plateaus, and shaded valley environments",
    "windy":                "persistent wind shaping the physical experience of coastal headlands, open hilltops, and exposed ridge terrain",
    "mild weather":         "moderate temperature and calm conditions with no weather extremes across outdoor environments",
    "humid":                "high atmospheric moisture content creating a dense heavy-air quality in lowland, jungle, and coastal environments",
    "overcast":             "cloud-covered sky producing diffuse soft light, muted colors, and a moody atmospheric quality over landscapes",
    "misty":                "thin mist or low cloud partially obscuring terrain and creating layered depth across highland and forest environments",
    "warm weather":         "comfortably warm temperatures supporting outdoor activity across tropical beaches and lowland environments",
    "freezing":             "below-zero temperatures producing ice, frost, and rare snow-covered highland terrain",
    "stormy":               "severe weather with heavy rain, strong wind, and dramatic sky conditions transforming the character of exposed environments",
    "clear sky":            "cloudless sky with maximum visibility, vivid blue overhead, and optimal conditions for panoramic landscape photography",
    "snowy":                "snow-covered terrain with white-coated highland landscapes and rare cold-weather mountain scenery",
    "tropical":             "warm humid equatorial climate with lush dense vegetation, high rainfall, and year-round green coastal environments",
    "breezy":               "light wind across coastal or open terrain producing a pleasant cooling effect without disrupting outdoor conditions",
    "balmy":                "warm and pleasantly calm outdoor air typical of tropical evenings and sheltered coastal environments",
    "pleasant weather":     "favorable outdoor conditions with moderate temperature, low wind, and good light for open-air environments",
    "scorching":            "extreme high heat transforming exposed outdoor environments into harsh, sun-baked, high-contrast landscapes",
    "chilly":               "cool to cold air temperature characteristic of highland mornings, mountain passes, and shaded forest environments",
    "crisp air":            "clean sharp cool air typical of high-altitude terrain, post-rain highland environments, and clear winter mornings",
    "muggy":                "hot and heavily humid air typical of lowland tropical environments in wet season",
    "hazy":                 "reduced visibility from heat haze or pollution creating soft-focus atmospheric conditions over urban and coastal landscapes",
    "rainy":                "active rainfall shaping the visual and physical environment with wet surfaces, green growth, and low cloud",
    "drizzly":              "light intermittent rain producing moist air, shiny surfaces, and a subdued grey-green atmospheric landscape",

    # ── English — timing ────────────────────────────────────
    "weekend":              "two-day period when short-distance outdoor destinations and nearby leisure environments see concentrated visitor activity",
    "long weekend":         "extended break of three or more days enabling access to destinations beyond typical day-trip range",
    "off-peak":             "low-visitor-volume period when popular destinations are quieter, less crowded, and more accessible",
    "low season":           "period of minimal tourist activity when destinations are uncrowded and natural environments are less disturbed",
    "high season":          "peak visitor period when popular coastal, cultural, and resort destinations operate at full capacity",
    "peak season":          "maximum demand period when iconic destinations are at their busiest and most visually animated",
    "new year":             "transition period marked by fireworks, lit-up urban environments, and festive public gatherings at city landmarks",
}

# ═════════════════════════════════════════════════════════════
# B. SOCIAL GROUP
# ═════════════════════════════════════════════════════════════
SOCIAL_GROUP: dict[str, str] = {
    # ── Vietnamese — solo ───────────────────────────────────
    "một mình":             "single traveler moving through environments independently, setting their own pace without group coordination",
    "tự đi":                "self-directed travel through environments without a guide or group, relying on personal navigation",

    # ── Vietnamese — couples ────────────────────────────────
    "cặp đôi":              "two people traveling together through shared environments, with access to couple-oriented spaces and accommodations",
    "vợ chồng":             "married couple moving through destinations together, typically favoring comfortable and private environments",
    "hai người":            "two-person group navigating destinations together with shared decision-making",
    "trăng mật":            "post-wedding travel through exclusive resort or scenic environments designed for newlywed couples",
    "hẹn hò":               "two-person outing through an environment selected for its visual appeal, atmosphere, or dining scene",

    # ── Vietnamese — family ─────────────────────────────────
    "gia đình":             "family group requiring safe, accessible, and activity-diverse environments",
    "cả nhà":               "full household traveling together across environments accommodating multiple needs and ages",
    "trẻ em":               "family with children requiring safe terrain, shallow water, and accessible facilities",
    "trẻ nhỏ":              "family with young children needing simple, safe, and easy-to-navigate environments",
    "em bé":                "family with an infant requiring calm, low-noise, and highly accessible environments",
    "ba mẹ":                "adult travelers with parents preferring comfortable, culturally rich, and accessible destinations",
    "ông bà":               "elderly couple or grandparents in calm, accessible, and culturally meaningful environments",
    "ông bà cháu":          "multigenerational group including grandparents and children requiring accessible and engaging environments",
    "nhiều thế hệ":         "three or more generations requiring varied accessibility and activity levels",
    
    # ── Vietnamese — elderly / adults ───────────────────────
    "người cao tuổi":       "elderly travelers requiring flat terrain, accessible infrastructure, and low physical demand",
    "người lớn tuổi":       "older adults preferring calm, comfortable, and easy-to-navigate environments",
    "người già":            "senior individuals in quiet, safe, and low-intensity environments",
    "cao tuổi":             "senior travelers favoring accessible, unhurried, and culturally oriented destinations",
    "người lớn":            "adult travelers without child-related constraints, often prioritizing comfort or experience quality",
    "người trưởng thành":   "mature travelers seeking refined, comfortable, or culturally meaningful environments",
    "thiếu niên":           "teenagers or youth groups in active, social, and moderately adventurous environments",
    "thanh niên":           "young adult group moving through active, social, and energetic destination environments",

    # ── Vietnamese — friends ────────────────────────────────
    "bạn bè":               "peer group moving through social, active, or shared-interest environments",
    "nhóm bạn":             "group of friends navigating destinations together with flexible movement and shared intent",
    "nhóm nhỏ":             "small group in intimate, less crowded, or off-the-beaten-path environments",
    "nhóm lớn":             "large group requiring organized spaces and capacity for group-based activities",
    "hội bạn":              "casual friend group in lively, social, and experience-driven environments",
    "team":                 "informal peer group moving through active, social, or coordinated environments",

    # ── Vietnamese — work/specific groups ───────────────────
    "đồng nghiệp":          "workplace colleagues traveling together through organized team environments or conference destinations",
    "công ty":              "corporate group navigating organized destination environments for professional retreat or team-building",
    "sinh viên":            "young student group moving through affordable, social, and high-energy destination environments",

    # ── English — solo ──────────────────────────────────────
    "solo":                 "single traveler navigating environments independently without group coordination or companion constraints",

    # ── English — couples ───────────────────────────────────
    "couple":               "two-person romantic travel through environments suited for private, scenic, and intimate experiences",
    "newlyweds":            "newly married couple traveling through exclusive and visually striking resort or scenic environments",
    "honeymoon":            "post-wedding travel through private, luxurious, and scenically rich destination environments",
    "anniversary trip":     "return or special travel through meaningful, scenic, or high-quality destination environments",

    # ── English — family ────────────────────────────────────
    "family":               "multi-person family group requiring destinations with safe access, varied activities, and comfortable facilities",
    "kids":                 "family group including children requiring shallow water, safe terrain, and child-accessible environments",
    "baby":                 "travel with an infant requiring calm, flat, and facility-rich destination environments",
    "parents":              "adult traveling with elderly parents through accessible, scenic, and culturally engaging environments",
    "multigenerational":    "group spanning multiple age generations requiring destinations with varied accessibility and experience levels",

    # ── English — friends ───────────────────────────────────
    "friends":              "peer group navigating social, active, or culturally rich environments together",
    "group trip":           "multi-person travel requiring destinations that support shared activities and group logistics",
    "small group":          "intimate group preferring less crowded and more flexible environments",
    "large group":          "large party requiring organized spaces and scalable services",
    "girls trip":           "female group in social, scenic, or wellness-oriented environments",
    "guys trip":            "male group in active, social, or adventure-focused environments",
    "bachelorette":         "pre-wedding celebration in festive, social, and entertainment-driven environments",
    "bachelor":             "pre-wedding group travel in active, social, or outdoor-oriented environments",

    # ── English — work/specific ─────────────────────────────
    "corporate":            "professional group navigating structured destination environments for business retreat or team coordination",
    "students":             "young student group moving through affordable, high-energy, and socially active destination environments",
    "elderly":              "older travelers requiring flat, accessible, and low-physical-demand destination environments",
    "retirees":             "retired individuals moving through accessible, culturally meaningful, and unhurried destination environments",
}

# ═════════════════════════════════════════════════════════════
# C. TRIP DURATION
# ═════════════════════════════════════════════════════════════
TRIP_DURATION: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "một ngày":         "city attractions, cafes, parks, nearby scenic spots",
    "một đêm":          "small towns, nature areas, local destinations with both day and evening activities",
    "hai đêm":          "main destination with nearby attractions, varied environments, local experiences",
    "một tuần":         "multiple locations, cultural sites, diverse landscapes across a region",
    "hai tuần":         "several destinations, varied environments, deeper exploration",
    "dài ngày":         "multiple regions, diverse environments, immersive travel experiences",
    "ngắn ngày":        "nearby attractions, small towns, compact areas",
    "vài ngày":         "one main destination with a few surrounding locations",
    "một buổi":         "single place such as a cafe, attraction, or local spot",
    "vài giờ":          "quick visit to a cafe, park, or small local place",
    "qua đêm":          "single destination with evening and early morning atmosphere",

    # ── English ─────────────────────────────────────────────
    "day trip":         "city attractions, cafes, parks, nearby scenic spots",
    "overnight":        "single destination with evening and early morning atmosphere",
    "two days":         "one destination with a few nearby attractions or activities",
    "three days":       "one destination with varied environments and nearby experiences",
    "one week":         "multiple locations, cultural sites, diverse landscapes",
    "two weeks":        "several destinations, varied environments, deeper exploration",
    "weekend trip":     "small towns, nature spots, compact destinations",
    "long weekend":     "one destination with multiple experiences and nearby locations",
    "short trip":       "single destination or a small number of places",
    "long trip":        "multiple destinations with diverse environments and experiences",
    "half day":         "single place such as a cafe, attraction, or local spot",
    "fortnight":        "multiple destinations, broad range of environments",
}

# ═════════════════════════════════════════════════════════════
# D. TRIP DISTANCE
# ═════════════════════════════════════════════════════════════
TRIP_DISTANCE: dict[str, str] = {
    # ── Vietnamese keys → English descriptive phrases ───────
    "gần":          "a familiar and local place with a comfortable feel",
    "gần nhà":      "a very familiar everyday place close to where people live",
    "không xa":     "a place that feels easy and convenient to get to",
    "trong nước":   "a place within the country with a familiar cultural feel",
    "quốc tế":      "a place in another country with a new and different atmosphere",
    "nước ngoài":   "a foreign place that feels unfamiliar and new",
    "xa":           "a place that feels more distant and less familiar",
    "xa xôi":       "a remote and isolated place with a quiet rural feel",
    "trong tỉnh":   "a local place within the same area with a familiar setting",
    "ngoại ô":      "a quieter suburban place slightly away from the center",

    # ── English keys ────────────────────────────────────────
    "nearby":           "a familiar and local place with a comfortable feel",
    "close to home":    "a very familiar everyday place close to where people live",
    "not far":          "a place that feels easy and convenient to get to",
    "domestic":         "a place within the country with a familiar cultural feel",
    "international":    "a place in another country with a new and different atmosphere",
    "overseas":         "a foreign place that feels unfamiliar and new",
    "far away":         "a place that feels more distant and less familiar",
    "regional":         "a place within a nearby region with a local feel",
    "cross-country":    "places across the country with varied regional character",
}

# ═════════════════════════════════════════════════════════════
# E. BUDGET LEVEL
# ═════════════════════════════════════════════════════════════
BUDGET_LEVEL: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "tiết kiệm":            "low-cost travel through destinations with affordable accommodation, street food, and free or low-entry attractions",
    "bình dân":             "moderately priced destinations with comfortable mid-range accommodation and local dining options",
    "sang trọng":           "high-end destination environments featuring luxury resorts, fine dining venues, and premium service facilities",
    "cao cấp":              "upscale destination environments with premium facilities, exclusive access, and high-quality service infrastructure",
    "giá rẻ":               "budget destination environments where costs are minimal and local, informal, and street-level experiences dominate",
    "vừa túi":              "destinations priced within an affordable range without sacrificing basic comfort or quality",
    "hạng sang":            "luxury-tier destination environments with five-star properties, exclusive venues, and premium amenities",
    "5 sao":                "five-star destination environments featuring world-class resort facilities, gourmet dining, and high-end services",

    # ── English ─────────────────────────────────────────────
    "budget":               "low-cost destination environments dominated by hostels, street food, and free public attractions",
    "affordable":           "reasonably priced destinations offering comfort and value without premium pricing",
    "mid-range":            "destination environments with comfortable facilities, decent dining, and moderate pricing",
    "upscale":              "higher-end destination environments with quality accommodation, curated dining, and polished service",
    "luxury":               "premium destination environments featuring exclusive resorts, fine dining, and high-end private amenities",
    "splurge":              "destinations selected for exceptional or indulgent high-end experiences regardless of cost",
    "high-end":             "top-tier destination environments with premium infrastructure, exclusive venues, and luxury service standards",
    "5 star":               "five-star resort environments with world-class facilities, gourmet restaurants, and full-service amenities",
    "value for money":      "destinations offering a strong ratio of experience quality to cost across accommodation and activities",
    "free":                 "destinations or attractions with no entry cost, typically public parks, beaches, or open cultural sites",
}

# ═════════════════════════════════════════════════════════════
# F. PACE & STYLE
# ═════════════════════════════════════════════════════════════
PACE: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "chậm rãi":             "slow movement through destination environments with extended time at each location and minimal schedule pressure",
    "thư thả":              "leisurely exploration of environments without time constraints, allowing full absorption of each setting",
    "thoải mái":            "relaxed travel through destinations without rigid scheduling or physical demands",
    "năng động":            "active and fast-moving travel through multiple environments with high daily activity output",
    "tự do":                "unconstrained movement through destinations without pre-set routes or fixed itineraries",
    "có kế hoạch":          "structured travel through destinations following a pre-defined sequence of sites and environments",
    "linh hoạt":            "semi-structured travel through destinations with room for spontaneous changes in route or timing",
    "tự túc":               "self-guided movement through destinations without reliance on organized tours or external guides",
    "chill":                "very slow, low-pressure exploration of environments with no fixed agenda",
    "tự lái xe":            "self-drive travel through destination landscapes by private vehicle, enabling flexible off-route access",
    "theo tour":            "movement through destinations as part of an organized guided group with pre-planned site visits",
    "đi phượt":             "independent backpacker-style movement through destinations, often by motorbike, on flexible unplanned routes",

    # ── English ─────────────────────────────────────────────
    "leisurely":            "slow and unhurried movement through destination environments with extended time at each site",
    "relaxed":              "low-pressure travel through destinations without rigid scheduling or high physical demand",
    "packed itinerary":     "high-density travel through multiple destination environments in a compressed timeframe",
    "spontaneous":          "unplanned movement through destinations driven by real-time decisions rather than pre-set itineraries",
    "guided tour":          "organized movement through destination sites with expert narration and group logistics",
    "flexible":             "adaptable travel through destinations allowing real-time changes in route, pace, or location choice",
    "independent":          "self-directed movement through destinations without guides or pre-packaged tour structures",
    "self-drive":           "private vehicle travel through destination landscapes enabling off-route and flexible access",
    "backpacking":          "budget-conscious independent movement through multiple destination environments with minimal planning",
    "road trip":            "long-distance vehicle travel through sequential destination environments along a scenic or cultural route",
    "all-inclusive":        "resort-based travel where all destination services including accommodation, food, and activities are bundled",
    "slow travel":          "extended immersive presence in a single destination environment over days or weeks",
    "digital nomad":        "location-independent travel through destinations with reliable connectivity and workspace infrastructure",
    "workation":            "travel to a destination environment that balances remote work conditions with leisure access",
    "eco travel":           "travel through environmentally sensitive destination environments with low-impact access principles",
    "volunteer":            "travel to destination environments for community engagement or conservation participation",
}

# ═════════════════════════════════════════════════════════════
# G. NATURE & LANDSCAPE
# ═════════════════════════════════════════════════════════════
NATURE_LANDSCAPE: dict[str, str] = {
    # ── Vietnamese — general nature ─────────────────────────
    "thiên nhiên":          "natural outdoor environments away from urban development, characterized by vegetation, open terrain, and non-built scenery",
    "cảnh thiên nhiên":     "visual landscape of undeveloped natural terrain including forests, mountains, waterways, and open sky",
    "cảnh đẹp thiên nhiên": "visually striking natural scenery with distinctive landforms, vegetation, or water features suited for photography and observation",

    # ── Vietnamese — terrain ────────────────────────────────
    "núi":                  "elevated mountain terrain with defined peaks, steep slopes, forest cover, and high-altitude viewpoints",
    "đồi":                  "rolling hill terrain with gradual slopes, grassy or forested cover, and open views across countryside",
    "cao nguyên":           "elevated plateau terrain with wide-open grassland, moderate altitude, and expansive sky-filled views",
    "thung lũng":           "enclosed valley terrain between mountain ridges with river corridors, terraced fields, and layered highland scenery",
    "hang động":            "underground cave environment with geological rock formations, subterranean waterways, and dramatic interior spaces",
    "sa mạc":               "arid desert terrain with expansive sand dunes, minimal vegetation, and stark high-contrast visual landscapes",
    "đồng lúa":             "flat agricultural terrain covered in rice paddies with reflective water surfaces and seasonal green or golden color",
    "ruộng bậc thang":      "terraced hillside rice fields carved into mountain slopes, forming geometric visual patterns across highland terrain",
    "vách đá":              "vertical rock cliff face rising above coastal waters or valley floors, often forming dramatic natural viewpoints",

    # ── Vietnamese — water ──────────────────────────────────
    "biển":                 "open ocean or sea environment with sandy shoreline, wave action, salt water, and coastal cliff or bay formations",
    "bãi biển":             "sandy beach shoreline with direct sea access, typically featuring calm or moderate wave conditions",
    "biển xanh":            "clear turquoise seawater with high visibility and visually striking color typical of tropical coastal environments",
    "đảo":                  "island land mass surrounded by sea, typically featuring beaches, reef systems, and isolated coastal terrain",
    "vịnh":                 "sheltered bay or inlet with calm protected water enclosed by headlands or coastal cliff formations",
    "hồ":                   "inland lake environment with still reflective water surface, shoreline vegetation, and surrounding highland or forest terrain",
    "sông":                 "river environment with flowing water, riverside vegetation, sandbanks, and boat-navigable waterway corridors",
    "suối":                 "small freshwater stream with clear shallow water flowing through forested or rocky terrain",
    "thác nước":            "waterfall environment where water cascades vertically over rock faces into pools below, surrounded by forest or cliff",
    "rừng ngập mặn":        "coastal mangrove forest environment with dense root systems growing in brackish tidal water",
    "san hô":               "underwater coral reef environment with diverse marine ecosystems visible through clear shallow tropical water",
    "mạch nước nóng":       "natural geothermal hot spring environment with mineral-rich warm water emerging from ground in highland or volcanic terrain",
    "đầm phá":              "coastal lagoon environment with calm brackish water separated from the sea by narrow sandbars or coastal barriers",

    # ── Vietnamese — vegetation ─────────────────────────────
    "rừng":                 "dense forest environment with multi-layered tree canopy, undergrowth, and wildlife habitat away from human settlement",
    "rừng nhiệt đới":       "tropical rainforest with dense year-round canopy, high biodiversity, and intense green vegetation in humid climate",
    "vườn quốc gia":        "protected natural park environment with preserved ecosystems, wildlife habitats, and marked trail access",
    "rừng thông":           "highland pine forest environment with tall straight conifers, resinous scent, and cool shaded terrain",
    "đồng cỏ":              "open grassland terrain with low vegetation, wide sightlines, and unobstructed views across flat or gently rolling ground",
    "vườn hoa":             "cultivated flower garden with dense seasonal blooms across ordered or naturalistic landscape arrangements",
    "vườn trà":             "highland tea plantation with rows of low tea bushes extending across slopes in geometric green patterns",
    "đồi chè":              "tea-covered hillside terrain with rolling green rows of cultivated bushes set against highland sky",
    "vườn cà phê":          "coffee plantation environment with shaded trees and cultivated coffee plants in highland agricultural terrain",

    # ── Vietnamese — sky ────────────────────────────────────
    "bầu trời sao":         "dark-sky environment away from light pollution where stars, constellations, and the Milky Way are clearly visible",
    "bình minh":            "early morning environment when the sun rises and casts warm golden light across landscapes and water surfaces",
    "hoàng hôn":            "late afternoon environment when the sun descends toward the horizon and casts orange, pink, and red light across sky and terrain",
    "sương mù":             "fog or low cloud environment reducing visibility and creating atmospheric layered depth over highland or coastal terrain",

    # ── English — general ───────────────────────────────────
    "nature":               "natural outdoor environments away from urban development featuring undisturbed terrain, vegetation, and open sky",
    "wilderness":           "remote undeveloped natural environments far from human settlement with minimal infrastructure",
    "scenery":              "visual character of a natural or cultural landscape as experienced from a viewpoint or in transit",
    "landscape":            "broad visual composition of terrain, vegetation, water, and sky forming a natural or rural scene",

    # ── English — terrain ───────────────────────────────────
    "beach":                "sandy coastal shoreline environment with direct sea access, wave conditions, and open ocean views",
    "mountain":             "elevated peak terrain with steep slopes, high-altitude views, and distinct geological character",
    "hiking":               "trail-based movement through mountain, forest, or coastal terrain on foot-accessible natural paths",
    "trekking":             "multi-day foot travel through extended natural terrain covering mountain passes, forests, and remote valleys",
    "forest":               "dense tree-covered environment with canopy, undergrowth, shade, and wildlife habitat",
    "waterfall":            "vertical water cascade over a rock face into a pool below, typically set within forested or highland terrain",
    "lake":                 "inland body of still water with defined shoreline, reflective surface, and surrounding natural terrain",
    "cave":                 "underground geological environment with rock formations, enclosed passages, and subterranean features",
    "island":               "land mass surrounded by ocean or sea with beaches, reef systems, and isolated coastal character",
    "river":                "flowing freshwater environment with defined banks, current, and boat-navigable or swim-accessible sections",
    "sea":                  "open saltwater environment with waves, tidal movement, and expansive horizontal views to the horizon",
    "ocean":                "vast open saltwater body with deep water, wave systems, and uninterrupted views across the surface",
    "coast":                "land edge meeting the sea, featuring cliffs, beaches, coves, and coastal geological formations",
    "desert":               "arid landscape with minimal vegetation, expansive sand or rock terrain, and extreme temperature conditions",
    "jungle":               "dense tropical forest environment with layered vegetation, high humidity, and rich biodiversity",
    "valley":               "enclosed terrain between elevated ridges with river systems, flat agricultural land, and framed highland views",
    "cliff":                "steep vertical rock face rising above sea or valley floor, typically forming dramatic natural viewpoints",
    "hot spring":           "natural geothermal pool with warm mineral-rich water emerging from the ground in highland or volcanic environments",
    "rice field":           "flat agricultural terrain of cultivated rice paddy with reflective water and seasonal color changes",
    "rice terraces":        "stepped hillside rice cultivation carved into mountain slopes forming layered geometric visual patterns",
    "national park":        "protected ecological area with preserved natural terrain, wildlife habitats, and managed visitor access",
    "coral reef":           "underwater ecosystem of coral formations in clear tropical water supporting high marine biodiversity",
    "mangrove":             "coastal forest of salt-tolerant trees with exposed root systems growing in tidal and brackish water environments",
    "lagoon":               "calm enclosed coastal water body separated from the open sea by sand barriers or reef formations",
    "bay":                  "sheltered coastal inlet enclosed by headlands with calm water and protected anchorage",
    "tea plantation":       "highland agricultural landscape of ordered tea bush rows extending across cultivated slopes",
    "flower field":         "open terrain covered in dense seasonal wildflower or cultivated bloom creating vivid color across the landscape",
    "sunset":               "late-day environment when the sun approaches the horizon casting warm orange and red light across sky and terrain",
    "sunrise":              "early morning environment when the sun clears the horizon and illuminates landscapes with golden directional light",
    "stargazing":           "nighttime environment with minimal light pollution enabling clear visibility of stars and celestial features",
}

# ═════════════════════════════════════════════════════════════
# H. TRAVEL INTENT
# ═════════════════════════════════════════════════════════════
TRAVEL_INTENT: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "muốn trải nghiệm":     "desire to access a specific type of environment or activity for direct firsthand engagement",
    "muốn khám phá":        "intent to discover and move through unfamiliar destination environments through active exploration",
    "muốn tham quan":       "desire to visit and observe specific cultural, natural, or urban destination sites",
    "khám phá":             "active discovery-oriented movement through unfamiliar destination environments",
    "trải nghiệm":          "direct firsthand engagement with a destination environment, culture, or activity",
    "tham quan":            "structured observation visit to notable cultural, natural, or historical destination sites",
    "hành trình":           "a travel route or journey through a sequence of destination environments",

    # ── English ─────────────────────────────────────────────
    "vacation":             "an extended leisure travel period through destination environments away from home",
    "holiday":              "a dedicated leisure travel period through destination environments for rest or cultural engagement",
    "getaway":              "a short escape to a destination environment away from the everyday routine",
    "explore":              "discovery-oriented movement through unfamiliar destination terrain and environments",
    "discover":             "active encounter with previously unknown destination environments or cultural settings",
    "journey":              "an extended travel route through a sequence of destination environments",
    "sightseeing":          "observation-oriented movement through notable destination sites, landmarks, and viewpoints",
    "visit":                "a direct access trip to a specific destination site or environment",
}

# ═════════════════════════════════════════════════════════════
# I. MOOD & ATMOSPHERE
# ═════════════════════════════════════════════════════════════
MOOD_ATMOSPHERE: dict[str, str] = {
    # ── Vietnamese — tranquil ───────────────────────────────
    "yên tĩnh":             "environment characterized by low noise, minimal human activity, and a calm undisturbed physical atmosphere",
    "yên bình":             "calm and peaceful environmental setting with a gentle, unhurried physical character",
    "tĩnh lặng":            "silent or near-silent environment with very low ambient sound and minimal disturbance",
    "vắng vẻ":              "lightly visited environment with few other people present and an uncrowded physical atmosphere",
    "ẩn mình":              "concealed or hard-to-find location tucked away from main travel routes and tourist infrastructure",
    "riêng tư":             "private environment with restricted or exclusive access, limited to small groups or individuals",
    "hoang vắng":           "deserted or near-empty natural environment with no nearby human settlement or developed infrastructure",
    "hẻo lánh":             "physically remote location far from main roads and population centers",

    # ── Vietnamese — lively ─────────────────────────────────
    "sôi động":             "high-energy environment with dense activity, movement, sound, and a vibrant visual character",
    "nhộn nhịp":            "bustling environment with constant movement, crowds, vendors, and high ambient activity levels",
    "náo nhiệt":            "loud and crowded environment with festive energy, noise, and dense human activity",
    "tấp nập":              "busy environment with continuous foot traffic, commerce, and high human activity density",

    # ── Vietnamese — romantic ───────────────────────────────
    "lãng mạn":             "environment with a visually and atmospherically beautiful character suited for intimate two-person experiences",
    "thơ mộng":             "picturesque and poetic environment with soft light, natural beauty, and a dreamlike visual quality",
    "huyền ảo":             "ethereal and magical-feeling environment often enhanced by mist, unusual light, or dramatic natural formations",

    # ── Vietnamese — dramatic/wild ──────────────────────────
    "hùng vĩ":              "grand and imposing natural environment with large-scale landforms, dramatic terrain, and powerful visual presence",
    "hoang dã":             "wild and untamed natural environment with minimal human modification and raw ecological character",
    "nguyên sinh":          "pristine primary environment that has never been significantly altered by human activity",
    "huyền bí":             "mysterious atmospheric environment often defined by fog, unusual light, dense vegetation, or hidden terrain",

    # ── Vietnamese — cozy/warm ─────────────────────────────
    "ấm cúng":              "small enclosed environment with warm lighting, comfortable furnishings, and an intimate physical character",
    "ấm áp":                "warm and welcoming physical environment with comfortable temperature and an inviting character",

    # ── Vietnamese — modern/rustic ──────────────────────────
    "hiện đại":             "contemporary built environment with modern architecture, urban infrastructure, and current design aesthetics",
    "cổ kính":              "aged environment with visible historic architecture, worn surfaces, and an old-world visual character",
    "mộc mạc":              "rustic environment with natural materials, simple construction, and an unpolished traditional character",
    "hoài cổ":              "environment with a deliberately nostalgic aesthetic referencing older architectural styles and design periods",

    # ── Vietnamese — aesthetic ──────────────────────────────
    "đẹp như tranh":        "environment with a composition and visual quality resembling a painted landscape or artistic photograph",
    "đẹp":                  "visually attractive environment with notable aesthetic qualities across terrain, light, or built character",
    "nhiều màu sắc":        "visually vibrant environment with strong, varied, and saturated colors across its physical elements",

    # ── English ─────────────────────────────────────────────
    "quiet":                "environment with low ambient noise, minimal human activity, and an undisturbed physical character",
    "peaceful":             "calm and undisturbed environmental setting with a gentle, unhurried physical character",
    "tranquil":             "very calm and still environment with minimal movement, noise, or disturbance",
    "serene":               "exceptionally calm and visually harmonious environment with a composed and undisturbed quality",
    "secluded":             "physically separated or hidden environment with restricted access and very few visitors",
    "remote":               "geographically distant environment far from urban centers and established tourist infrastructure",
    "lively":               "high-energy environment with dense movement, activity, sound, and a vibrant social character",
    "vibrant":              "visually and energetically dynamic environment with strong color, activity, and sensory stimulation",
    "romantic":             "environment with visual and atmospheric qualities suited to intimate two-person experience",
    "dreamy":               "environment with soft light, unusual atmospheric conditions, and an otherworldly visual quality",
    "cozy":                 "small warm enclosed environment with comfortable physical conditions and intimate scale",
    "rustic":               "environment built from natural or traditional materials with an unpolished, aged character",
    "modern":               "contemporary built environment with current architecture, clean design, and urban infrastructure",
    "luxurious":            "high-end environment with premium materials, refined design, and exclusive physical conditions",
    "picturesque":          "environment with a composition and visual quality comparable to a scenic painting or photograph",
    "photogenic":           "environment with distinctive visual elements, good light, and strong photographic potential",
    "scenic":               "environment with notable natural or cultural visual character worth observing and photographing",
    "beautiful":            "environment with strong positive aesthetic qualities across its terrain, light, and composition",
    "stunning":             "environment with an exceptionally powerful and immediately striking visual impact",
    "magical":              "environment with an unusual or extraordinary atmosphere beyond ordinary physical expectations",
    "wild":                 "raw and unmodified natural environment with untamed ecological character",
    "pristine":             "completely unmodified natural environment in original ecological condition",
    "dramatic":             "environment with extreme-scale landforms, powerful weather, or intense visual contrasts",
    "colorful":             "visually vibrant environment with strong varied color across its physical elements",
    "hidden gem":           "lesser-known destination with high-quality physical environment not widely promoted or visited",
    "off the beaten path":  "destination removed from main tourist circuits with undeveloped access and few visitors",
    "unique":               "environment with distinctive or unusual physical characteristics not found in typical destinations",
    "authentic":            "environment that reflects genuine local or traditional character without tourist-oriented modification",
    "immersive":            "environment that fully surrounds and engages the visitor through its physical scale and sensory character",
}

# ═════════════════════════════════════════════════════════════
# J. ACTIVITIES (free-text signals)
# ═════════════════════════════════════════════════════════════
ACTIVITIES: dict[str, str] = {
    # ── Vietnamese — water ──────────────────────────────────
    "bơi lội":              "swimming in open water or pool environments including beaches, lakes, and resort facilities",
    "lặn biển":             "underwater diving through coral reef and marine environments using scuba or snorkel equipment",
    "chèo kayak":           "kayak paddling through coastal, river, or lake environments using a small human-powered vessel",
    "lướt sóng":            "surfing ocean waves on a board in open coastal environments with sufficient swell",
    "đi thuyền":            "boat travel through river, lake, or coastal environments for scenic transit or leisure",
    "câu cá":               "fishing from shoreline, boat, or pier in river, lake, or sea environments",
    "bơi hang":             "swimming through underground cave water passages in geological karst environments",

    # ── Vietnamese — land ───────────────────────────────────
    "leo núi":              "ascending mountain terrain on foot through trail or off-trail highland environments",
    "đi bộ đường dài":      "extended multi-day foot travel through wilderness mountain or forest terrain",
    "leo thác":             "trekking to and through waterfall environments including wet rock scrambling",
    "đạp xe":               "cycling through scenic countryside, coastal roads, or urban environments by bicycle",
    "cưỡi ngựa":            "horseback travel through open rural, coastal, or highland terrain",
    "leo vách đá":          "vertical ascent of natural rock cliff faces using climbing equipment in outdoor environments",
    "zipline":              "aerial traverse through forest or valley environments via cable between elevated platforms",
    "cắm trại":             "overnight stay in a natural outdoor environment using tent or basic shelter",
    "dã ngoại":             "outdoor gathering in a natural or park environment for leisure without overnight stay",
    "đi jeep":              "off-road vehicle travel through rough highland or rural terrain inaccessible by standard vehicles",
    "trượt cát":            "descending sand dune faces on a board in desert or coastal dune environments",

    # ── Vietnamese — air ────────────────────────────────────
    "dù lượn":              "unpowered gliding flight through highland or coastal air currents from elevated launch points",
    "khinh khí cầu":        "hot air balloon flight over scenic terrain at low altitude during early morning conditions",
    "cáp treo":             "aerial gondola transit over mountainous terrain between valley and highland elevation points",

    # ── Vietnamese — wellness ───────────────────────────────
    "spa":                  "dedicated wellness facility offering body treatments, massage, and therapeutic services",
    "massage":              "therapeutic physical treatment of muscle and soft tissue in a dedicated wellness environment",
    "yoga":                 "structured physical and meditative practice conducted in indoor or outdoor natural environments",
    "thiền":                "silent mindfulness practice conducted in quiet natural or dedicated retreat environments",
    "tắm bùn":              "mineral mud bath treatment in a natural or spa-facility thermal environment",
    "tắm suối khoáng":      "immersion in natural geothermal mineral spring water in highland or volcanic terrain",
    "tắm lá thuốc":         "herbal medicinal bath using traditional plant-based preparations in highland ethnic community settings",

    # ── Vietnamese — cultural ───────────────────────────────
    "nấu ăn":               "hands-on culinary preparation in a kitchen environment using local ingredients and techniques",
    "làm gốm":              "hands-on ceramic shaping and firing in a traditional craft village or artisan workshop environment",
    "vẽ tranh":             "visual art creation in a studio, workshop, or outdoor scenic environment",
    "chụp ảnh":             "photographic documentation of landscapes, environments, cultural sites, or subjects",
    "ngắm chim":            "wildlife observation focused on bird species in wetland, forest, or coastal environments",
    "mua sắm":              "browsing and purchasing goods in market, boutique, or retail environments",

    # ── English ─────────────────────────────────────────────
    "swimming":             "water immersion and movement in open sea, lake, river, or pool environments",
    "diving":               "underwater exploration of marine environments using scuba equipment",
    "snorkeling":           "surface-level underwater observation of reef and marine environments using mask and fins",
    "kayaking":             "small paddle-vessel travel through coastal, river, or lake water environments",
    "surfing":              "wave-riding on a board in open coastal ocean environments with active swell",
    "fishing":              "angling activity in river, lake, sea, or estuary environments from shore or vessel",
    "boating":              "leisure or transit travel through water environments by motorized or sailing vessel",
    "cycling":              "bicycle travel through scenic road, trail, or urban environments",
    "trekking":             "extended foot travel through mountain, forest, or wilderness terrain over multiple days",
    "hiking":               "day-range foot travel along marked trails through natural terrain",
    "climbing":             "vertical ascent of natural rock or mountain terrain using physical and equipment-based techniques",
    "rock climbing":        "technical ascent of natural cliff or boulder terrain in outdoor environments",
    "camping":              "overnight stay in a natural outdoor environment using tent or minimal shelter",
    "zip line":             "cable-based aerial traverse through forest or valley environments at height",
    "paragliding":          "unpowered gliding flight through highland air currents launched from elevated terrain",
    "hot air balloon":      "balloon flight at low altitude over scenic terrain in calm early morning conditions",
    "cable car":            "enclosed aerial gondola transit over mountainous or elevated terrain",
    "photography":          "image capture of landscapes, environments, subjects, and cultural sites",
    "cooking class":        "structured hands-on culinary instruction using local ingredients in a kitchen environment",
    "pottery":              "hands-on ceramic shaping in a traditional craft or artisan workshop environment",
    "yoga retreat":         "structured multi-day program of yoga and meditation practice in a dedicated natural or resort environment",
    "meditation":           "silent mindfulness practice in a quiet natural, retreat, or dedicated indoor environment",
    "birdwatching":         "wildlife observation activity focused on bird species in wetland, forest, or coastal terrain",
    "wildlife watching":    "observation of animals in their natural habitat across forest, wetland, or marine environments",
    "motorbike tour":       "self-guided or guided travel through destination landscapes by motorbike on scenic roads",
    "jeep tour":            "off-road vehicle travel through rough or remote highland and rural terrain",
    "mud bath":             "therapeutic mineral mud immersion in natural or spa-facility thermal environments",
    "sandboarding":         "board descent of sand dune faces in desert or coastal dune terrain",
    "horse riding":         "horseback travel through open rural, coastal, or highland environmental terrain",
    "picnic":               "outdoor meal in a natural park, garden, or scenic environment without fixed facilities",
    "shopping":             "browsing and purchasing in market, boutique, craft village, or retail environments",
    "sightseeing":          "structured observation visits to notable destination landmarks, cultural sites, and viewpoints",
    "boat cruise":          "scenic vessel travel through river, coastal, or bay environments for observation",
    "food tour":            "sequential visit to multiple food vendors, markets, or restaurants across a destination environment",
    "cultural show":        "observation of traditional performing arts in an indoor venue or open cultural environment",
}

# ═════════════════════════════════════════════════════════════
# K. FOOD & DRINK
# ═════════════════════════════════════════════════════════════
FOOD_DRINK: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "ẩm thực":              "food-focused environment with a wide variety of dishes, dining styles, and local culinary experiences",
    "ăn uống":              "casual dining environment with a mix of food stalls, restaurants, and local eating spots",
    "ẩm thực địa phương":   "regional cuisine specific to a destination, prepared with local ingredients and traditional cooking methods",
    "hải sản":              "seafood-focused cuisine featuring fresh fish, shrimp, crab, and shellfish from coastal or river environments",
    "món chay":             "plant-based cuisine without meat or animal products, typically available near temples or health-oriented establishments",
    "đồ ăn đường phố":      "informal food served from street stalls or mobile vendors in market, sidewalk, or night-market environments",
    "cà phê":               "Vietnamese coffee culture environment including traditional drip, egg coffee, and café street culture",
    "bia hơi":              "draft beer culture in informal streetside venues typical of northern Vietnamese urban neighborhoods",
    "trà":                  "tea culture environment including highland plantation tasting, traditional ceremony, and café service",
    "đặc sản":              "signature local specialty dishes unique to a specific destination region or community",
    "chợ đêm":              "nighttime market environment with street food stalls, vendor activity, and open-air dining conditions",

    # ── English ─────────────────────────────────────────────
    "local food":           "cuisine specific to a destination region prepared with local ingredients and traditional methods",
    "street food":          "informal food served from street-level vendors, stalls, and mobile carts in open market environments",
    "seafood":              "ocean or river-sourced dishes featuring fresh fish, shellfish, and coastal-catch cuisine",
    "vegetarian":           "plant-based cuisine without meat, widely available near temples, health cafés, and tourist environments",
    "vegan":                "strictly plant-based cuisine with no animal products in any form",
    "fine dining":          "high-end restaurant environment with formal service, curated menus, and premium ingredients",
    "coffee":               "coffee-focused café environment with varied preparation styles and local roasting traditions",
    "restaurant":           "sit-down dining environment with table service and a defined menu of prepared dishes",
    "food tour":            "sequential guided or self-directed visit to multiple food vendors across a destination environment",
    "night market":         "evening outdoor market environment with concentrated street food stalls and vendor activity",
    "wine":                 "wine-focused dining or tasting environment including vineyard visits and paired restaurant service",
    "tasting":              "structured sampling of multiple food or beverage items in a culinary or agricultural environment",
}

# ═════════════════════════════════════════════════════════════
# L. ACCOMMODATION
# ═════════════════════════════════════════════════════════════
ACCOMMODATION: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "khách sạn":            "multi-room commercial lodging facility in urban or resort environments with standard hotel amenities",
    "resort":               "large integrated lodging complex in coastal or natural environments with on-site pool, dining, and activity facilities",
    "villa":                "private standalone residence with exclusive access, typically featuring a private pool and garden environment",
    "homestay":             "accommodation within or adjacent to a local family's residence in a community or village environment",
    "nhà nghỉ":             "small informal guesthouse with basic facilities in local neighborhoods or rural environments",
    "hostel":               "shared dormitory-style accommodation in social environments popular with budget independent travelers",
    "bungalow":             "standalone low-rise accommodation unit in tropical beach or resort environments",
    "glamping":             "elevated outdoor accommodation combining tent or natural structure with premium comfort facilities",
    "nhà trên cây":         "elevated treehouse accommodation built into forest canopy in natural highland or jungle environments",
    "nhà thuyền":           "floating accommodation on river or lake water surfaces typical of certain Vietnamese waterway environments",
    "ecolodge":             "low-impact accommodation integrated into natural environments with sustainable construction and materials",
    "view biển":            "accommodation with direct visual access to ocean or coastal sea views",
    "view núi":             "accommodation with direct visual access to mountain or highland terrain views",

    # ── English ─────────────────────────────────────────────
    "hotel":                "commercial multi-room lodging in urban or resort environments with standard service amenities",
    "guesthouse":           "small informal lodging with basic facilities in local residential or rural environments",
    "hostel":               "shared dormitory accommodation in social environments for budget independent travelers",
    "villa":                "private standalone residence with exclusive access and typically a private pool or garden",
    "resort":               "large integrated coastal or natural lodging complex with pool, dining, and activity facilities",
    "homestay":             "accommodation within a local family residence in a community or village environment",
    "treehouse":            "elevated accommodation built into tree canopy in forest or jungle environments",
    "ecolodge":             "sustainably constructed low-impact accommodation integrated into natural terrain",
    "cabin":                "small rustic timber structure in forest or mountain environments with basic shelter facilities",
    "overwater bungalow":   "standalone accommodation unit built on stilts over tropical lagoon or reef water",
    "beachfront":           "accommodation with direct physical access to a sandy beach shoreline environment",
    "ocean view":           "accommodation with direct visual access to open ocean or sea from windows or terrace",
    "private pool":         "accommodation featuring an exclusive pool not shared with other guests",
    "infinity pool":        "resort pool designed with a vanishing edge creating a visual merge with the horizon or scenic background",
}

# ═════════════════════════════════════════════════════════════
# M. CULTURAL & HERITAGE
# ═════════════════════════════════════════════════════════════
CULTURAL_HERITAGE: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "văn hóa":              "shared customs, traditions, arts, and social practices shaping the identity of a destination community",
    "văn hóa địa phương":   "the customs, traditions, daily practices, and social character specific to a destination community",
    "lịch sử":              "physical remnants and documented record of past human activity at a destination, including monuments and ruins",
    "di tích lịch sử":      "preserved physical site of historical significance with remaining original structures or archaeological features",
    "di sản thế giới":      "UNESCO-designated site recognized for outstanding universal cultural or natural heritage value",
    "kiến trúc":            "built environment reflecting historical styles, structural design, and cultural influences of a destination",
    "phố cổ":               "historic old town district with preserved traditional street layout, architecture, and commercial character",
    "nhà cổ":               "traditional house preserved with historical architecture, materials, and cultural living patterns",
    "cung điện":            "royal palace complex with ceremonial halls, courtyards, and architecture associated with historical dynasties",
    "thành cổ":             "fortified historical structure or citadel with walls, gates, and defensive architectural elements",
    "lăng tẩm":             "royal tomb complex with ceremonial architecture, landscaped grounds, and cultural symbolism",
    "tín ngưỡng":           "spiritual belief system expressed through rituals, worship practices, and sacred community spaces",
    "đền":                  "Vietnamese shrine structure dedicated to spiritual figures or deified historical personalities",
    "chùa":                 "Buddhist temple complex with pagoda towers, worship halls, and landscaped grounds in traditional Vietnamese style",
    "nhà thờ":              "Christian church building, often featuring French colonial architecture in Vietnamese urban and rural environments",
    "đình":                 "communal house serving as a village cultural and spiritual center for gatherings and traditional ceremonies",
    "miếu":                 "small shrine structure dedicated to local spirits or deities within community environments",
    "văn miếu":             "Confucian temple complex associated with education, scholarship, and historical academic traditions",
    "dân tộc thiểu số":     "ethnic minority community with distinct language, costume, architecture, and cultural practices in highland regions",
    "lễ hội truyền thống":  "periodic cultural ceremony with traditional costumes, rituals, performances, and community gathering",
    "làng nghề":            "traditional craft village where specific artisan skills are practiced and passed between generations",
    "thủ công mỹ nghệ":     "handcrafted objects produced using traditional techniques in artisan village or workshop environments",
    "bảo tàng":             "institution housing collections of cultural, historical, or natural artifacts in organized exhibition environments",

    # ── English ─────────────────────────────────────────────
    "cultural":             "relating to the customs, arts, practices, and social character of a destination community",
    "heritage":             "physical and intangible remnants of historical human activity preserved in destination environments",
    "history":              "documented record of past events embodied in monuments, ruins, museums, and architectural environments",
    "UNESCO":               "site recognized by UNESCO for outstanding universal cultural or natural heritage significance",
    "architecture":         "built environment reflecting historical styles, design, and cultural influences across structures and spaces",
    "old town":             "historic district with preserved traditional architecture, street layout, and community character",
    "historic house":       "preserved residential structure reflecting traditional architecture and cultural living patterns",
    "palace":               "royal complex with ceremonial halls, courtyards, and architecture associated with historical governance",
    "citadel":              "fortified historical structure with defensive walls, gates, and strategic architectural design",
    "tomb":                 "burial site or complex with cultural, spiritual, and architectural significance",
    "colonial":             "built environment featuring French colonial architecture from Vietnam's 19th and early 20th century period",
    "religion":             "organized system of spiritual practices, worship spaces, and cultural traditions",
    "belief":               "spiritual or cultural belief system expressed through rituals and community practices",
    "temple":               "religious structure dedicated to spiritual worship and ritual practice in a sacred environment",
    "pagoda":               "multi-tiered Buddhist tower structure forming the visual centerpiece of Vietnamese temple complexes",
    "shrine":               "small sacred structure dedicated to spiritual figures or local deities",
    "communal house":       "village-centered structure used for gatherings, ceremonies, and shared cultural activities",
    "confucian":            "cultural and philosophical environment associated with education, scholarship, and traditional values",
    "ritual":               "structured ceremonial practice with prescribed traditional actions in a cultural or spiritual environment",
    "ethnic":               "community or destination defined by a distinct cultural identity, language, and traditional way of life",
    "festival":             "recurring public cultural event with traditional performances, costumes, rituals, and community gatherings",
    "craft village":        "community where traditional artisan skills are actively practiced and products made by hand",
    "handicraft":           "manually produced objects using traditional techniques in craft or artisan production environments",
    "museum":               "institution displaying historical, cultural, or natural collections in organized exhibition environments",
    "ancient":              "destination environment featuring structures or artifacts from periods centuries or millennia in the past",
    "traditional":          "destination environment reflecting practices, architecture, and customs passed down through generations",
}

# ═════════════════════════════════════════════════════════════
# N. WELLNESS & HEALTH
# ═════════════════════════════════════════════════════════════
WELLNESS_HEALTH: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "nghỉ dưỡng":           "restorative stay in a resort or natural environment oriented toward physical rest and recovery",
    "detox":                "structured cleansing program in a retreat environment eliminating processed food and external stimulation",
    "tĩnh tâm":             "silent meditative retreat in a quiet natural or dedicated spiritual environment",
    "sức khỏe":             "physical health-oriented travel through environments supporting fitness, fresh air, and active movement",
    "suối nước nóng":      "natural hot spring environment with mineral-rich water used for relaxation and physical recovery",
    "tắm khoáng":          "mineral bath environment in natural or spa settings supporting relaxation and therapeutic soaking",
    "thiền":               "meditation practice conducted in quiet natural or dedicated spiritual environments",
    "yoga":                "physical and mental practice performed in calm environments often integrated with nature or retreat settings",
    "spa":                 "facility offering relaxation and therapeutic treatments such as massage, sauna, and body care",

    # ── English ─────────────────────────────────────────────
    "wellness":             "travel through environments specifically designed or suited to support physical and mental health",
    "wellness retreat":     "structured multi-day program in a natural or dedicated facility oriented toward health and recovery",
    "healing":              "restorative environment supporting physical or psychological recovery through nature, quiet, or treatment",
    "detox":                "immersive program in a clean natural environment structured to eliminate stimulation and restore baseline health",
    "mindfulness":          "practice of present-moment awareness typically conducted in quiet natural or retreat environments",
    "meditation retreat":   "structured multi-day silent meditation program in a dedicated retreat facility or natural environment",
    "yoga retreat":         "structured multi-day yoga and meditation program in a natural or resort environment",
    "spa retreat":          "immersive stay at a dedicated spa facility with full-service wellness treatments over multiple days",
    "self care":            "deliberate rest and restoration in a comfortable environment away from daily demands",
    "burnout recovery":     "restorative travel through calm and low-stimulation natural environments to recover from prolonged overwork",
    "mental health":        "travel to environments supporting psychological restoration through nature, quiet, and reduced pressure",
    "rejuvenate":           "physical and mental restoration through exposure to restorative natural or spa environments",
    "hot spring":          "natural geothermal water environment used for soaking, relaxation, and physical recovery",
    "onsen":               "Japanese-style hot spring bathing environment with mineral water and structured relaxation rituals",
    "spa":                 "facility providing therapeutic treatments including massage, sauna, and body care in a controlled environment",
    "massage":             "body treatment practice focused on physical relaxation and muscle recovery in a spa or wellness setting",
    "sauna":               "heated enclosed environment used for sweating, relaxation, and physical recovery",
    "cold plunge":         "cold water immersion environment used for recovery, circulation, and contrast therapy",
    "yoga":                "physical and mental practice performed in calm environments often integrated with nature or retreats",
    "meditation":          "quiet mental practice conducted in low-stimulation environments for focus and awareness",
}

# ═════════════════════════════════════════════════════════════
# O. PHOTOGRAPHY & CONTENT
# ═════════════════════════════════════════════════════════════
PHOTOGRAPHY_CONTENT: dict[str, str] = {
    # ── Vietnamese ──────────────────────────────────────────
    "chụp ảnh":             "photographic documentation of landscapes, cultural sites, or subjects using a camera in destination environments",
    "check-in":             "social media location tagging at a visually distinctive or well-known destination site",
    "điểm check-in đẹp":    "destination location with strong visual identity commonly used as a social media photography subject",
    "quay phim":            "video recording of destination environments including drone, handheld, and cinematic footage",
    "cảnh sống ảo":         "highly photogenic environment with strong visual elements frequently used for social media content",
    "drone":                "aerial photography of destination landscapes using a remotely piloted camera-equipped aircraft",
    "hoàng hôn":           "sunset lighting condition with warm tones and directional light across landscapes",
    "bình minh":           "sunrise lighting condition with soft early light and atmospheric color gradients",
    "toàn cảnh":           "wide-angle view capturing a broad scene or landscape in a single frame",
    "cận cảnh":            "close-up composition focusing on details, textures, or specific subjects",

    # ── English ─────────────────────────────────────────────
    "photography":          "image capture of landscapes, natural environments, cultural sites, and subjects at a destination",
    "instagram":            "visually distinctive destination environment with strong social media photographic potential",
    "instagrammable":       "environment with composition, color, and visual character highly suited to social media image sharing",
    "content creation":     "systematic production of photo and video material from destination environments for digital publication",
    "drone shot":           "aerial image or video of destination landscapes captured from a remotely operated camera aircraft",
    "golden hour":          "early morning or late afternoon period when low-angle sunlight produces warm directional light across terrain",
    "landscape photography":"photographic practice focused on capturing broad natural terrain, sky, and environmental compositions",
    "photo spot":           "specific location within a destination known for its strong photographic framing or visual character",
    "scenic views":         "open viewpoints with broad unobstructed visual access to natural or cultural landscape compositions",
    "viewpoint":            "elevated or positioned observation point with wide-angle visual access to surrounding destination terrain",
    "sunset":              "low-angle evening light producing warm tones and long shadows across landscapes",
    "sunrise":             "early morning light with soft illumination and atmospheric color transitions",
    "wide angle":          "composition capturing a broad field of view including landscape and surrounding context",
    "close up":            "composition focusing on fine details or a specific subject within the environment",
    "portrait":            "photographic composition centered on a person as the primary subject within a setting",
    "aesthetic":           "visually styled environment with cohesive color, composition, and design elements",
}

# ═════════════════════════════════════════════════════════════
# MASTER REGISTRY
# ═════════════════════════════════════════════════════════════
ALL_CONTEXT: dict[str, str] = {
    **SEASON_WEATHER,
    **SOCIAL_GROUP,
    **TRIP_DURATION,
    **TRIP_DISTANCE,
    **BUDGET_LEVEL,
    **PACE,
    **NATURE_LANDSCAPE,
    **TRAVEL_INTENT,
    **MOOD_ATMOSPHERE,
    **ACTIVITIES,
    **FOOD_DRINK,
    **ACCOMMODATION,
    **CULTURAL_HERITAGE,
    **WELLNESS_HEALTH,
    **PHOTOGRAPHY_CONTENT,
}