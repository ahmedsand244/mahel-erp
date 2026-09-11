/* Bearing dataset — local, zero-latency (<10ms queries)
   Dimensions in mm. Sources: SKF / ISO metric tables.
   type: deep | thin-6800 | thin-6900 | thin-16000 | mini | tapered | angular | spherical
*/
window.BEARINGS = [
  // ---- Miniature ----
  {code:"623", d:3, D:10, B:4, type:"mini"},
  {code:"624", d:4, D:13, B:5, type:"mini"},
  {code:"625", d:5, D:16, B:5, type:"mini"},
  {code:"626", d:6, D:19, B:6, type:"mini"},
  {code:"627", d:7, D:22, B:7, type:"mini"},
  {code:"628", d:8, D:24, B:8, type:"mini"},
  {code:"629", d:9, D:26, B:8, type:"mini"},
  {code:"608", d:8, D:22, B:7, type:"mini", popular:1},
  {code:"609", d:9, D:24, B:7, type:"mini"},
  // ---- 6000 series ----
  {code:"6000", d:10, D:26, B:8, type:"deep"},
  {code:"6001", d:12, D:28, B:8, type:"deep", popular:1},
  {code:"6002", d:15, D:32, B:9, type:"deep"},
  {code:"6003", d:17, D:35, B:10, type:"deep"},
  {code:"6004", d:20, D:42, B:12, type:"deep", popular:1},
  {code:"6005", d:25, D:47, B:12, type:"deep"},
  {code:"6006", d:30, D:55, B:13, type:"deep"},
  {code:"6007", d:35, D:62, B:14, type:"deep"},
  {code:"6008", d:40, D:68, B:15, type:"deep"},
  {code:"6009", d:45, D:75, B:16, type:"deep"},
  {code:"6010", d:50, D:80, B:16, type:"deep"},
  {code:"6011", d:55, D:90, B:18, type:"deep"},
  {code:"6012", d:60, D:95, B:18, type:"deep"},
  // ---- 6200 series ----
  {code:"6200", d:10, D:30, B:9, type:"deep", popular:1},
  {code:"6201", d:12, D:32, B:10, type:"deep", popular:1},
  {code:"6202", d:15, D:35, B:11, type:"deep"},
  {code:"6203", d:17, D:40, B:12, type:"deep", popular:1},
  {code:"6204", d:20, D:47, B:14, type:"deep", popular:1},
  {code:"6205", d:25, D:52, B:15, type:"deep", popular:1},
  {code:"6206", d:30, D:62, B:16, type:"deep", popular:1},
  {code:"6207", d:35, D:72, B:17, type:"deep"},
  {code:"6208", d:40, D:80, B:18, type:"deep"},
  {code:"6209", d:45, D:85, B:19, type:"deep"},
  {code:"6210", d:50, D:90, B:20, type:"deep", popular:1},
  {code:"6211", d:55, D:100, B:21, type:"deep"},
  {code:"6212", d:60, D:110, B:22, type:"deep"},
  {code:"6213", d:65, D:120, B:23, type:"deep"},
  // ---- 6300 series ----
  {code:"6300", d:10, D:35, B:11, type:"deep"},
  {code:"6301", d:12, D:37, B:12, type:"deep", popular:1},
  {code:"6302", d:15, D:42, B:13, type:"deep", popular:1},
  {code:"6303", d:17, D:47, B:14, type:"deep"},
  {code:"6304", d:20, D:52, B:15, type:"deep", popular:1},
  {code:"6305", d:25, D:62, B:17, type:"deep", popular:1},
  {code:"6306", d:30, D:72, B:19, type:"deep"},
  {code:"6307", d:35, D:80, B:21, type:"deep"},
  {code:"6308", d:40, D:90, B:23, type:"deep"},
  {code:"6309", d:45, D:100, B:25, type:"deep", popular:1},
  {code:"6310", d:50, D:110, B:27, type:"deep"},
  {code:"6311", d:55, D:120, B:29, type:"deep"},
  {code:"6312", d:60, D:130, B:31, type:"deep"},
  // ---- 6800 thin ----
  {code:"6800", d:10, D:19, B:5, type:"thin"},
  {code:"6801", d:12, D:21, B:5, type:"thin"},
  {code:"6802", d:15, D:24, B:5, type:"thin"},
  {code:"6803", d:17, D:26, B:5, type:"thin"},
  {code:"6804", d:20, D:32, B:7, type:"thin"},
  {code:"6805", d:25, D:37, B:7, type:"thin"},
  {code:"6806", d:30, D:42, B:7, type:"thin"},
  {code:"6807", d:35, D:47, B:7, type:"thin"},
  {code:"6808", d:40, D:52, B:7, type:"thin"},
  {code:"6809", d:45, D:58, B:7, type:"thin"},
  {code:"6810", d:50, D:65, B:7, type:"thin"},
  // ---- 6900 thin ----
  {code:"6900", d:10, D:22, B:6, type:"thin"},
  {code:"6901", d:12, D:24, B:6, type:"thin"},
  {code:"6902", d:15, D:28, B:7, type:"thin"},
  {code:"6903", d:17, D:30, B:7, type:"thin"},
  {code:"6904", d:20, D:37, B:9, type:"thin"},
  {code:"6905", d:25, D:42, B:9, type:"thin"},
  {code:"6906", d:30, D:47, B:9, type:"thin"},
  {code:"6907", d:35, D:55, B:10, type:"thin"},
  {code:"6908", d:40, D:62, B:12, type:"thin"},
  {code:"6909", d:45, D:68, B:12, type:"thin"},
  {code:"6910", d:50, D:72, B:12, type:"thin"},
  // ---- 16000 thin open ----
  {code:"16000", d:10, D:26, B:8, type:"thin16000"},
  {code:"16001", d:12, D:28, B:8, type:"thin16000"},
  {code:"16002", d:15, D:32, B:8, type:"thin16000"},
  {code:"16003", d:17, D:35, B:8, type:"thin16000"},
  {code:"16004", d:20, D:42, B:8, type:"thin16000"},
  {code:"16005", d:25, D:47, B:8, type:"thin16000"},
  {code:"16006", d:30, D:55, B:9, type:"thin16000"},
  {code:"16007", d:35, D:62, B:9, type:"thin16000"},
  {code:"16008", d:40, D:68, B:9, type:"thin16000"},
  {code:"16009", d:45, D:75, B:10, type:"thin16000"},
  {code:"16010", d:50, D:80, B:10, type:"thin16000"},
  {code:"16011", d:55, D:90, B:11, type:"thin16000"},
  // ---- Tapered roller 30200 (T = width) ----
  {code:"30203", d:17, D:40, B:13.25, type:"tapered"},
  {code:"30204", d:20, D:47, B:15.25, type:"tapered", popular:1},
  {code:"30205", d:25, D:52, B:16.25, type:"tapered", popular:1},
  {code:"30206", d:30, D:62, B:17.25, type:"tapered", popular:1},
  {code:"30207", d:35, D:72, B:18.25, type:"tapered", popular:1},
  {code:"30208", d:40, D:80, B:19.75, type:"tapered"},
  {code:"30209", d:45, D:85, B:20.75, type:"tapered"},
  {code:"30210", d:50, D:90, B:21.75, type:"tapered"},
  {code:"30304", d:20, D:52, B:22.25, type:"tapered"},
  {code:"30305", d:25, D:62, B:25.25, type:"tapered"},
  {code:"30306", d:30, D:72, B:30.75, type:"tapered"},
  {code:"30307", d:35, D:80, B:32.75, type:"tapered"},
  {code:"32004", d:20, D:42, B:15, type:"tapered"},
  {code:"32005", d:25, D:47, B:15, type:"tapered"},
  {code:"32006", d:30, D:55, B:17, type:"tapered"},
  {code:"32007", d:35, D:62, B:18, type:"tapered"},
  {code:"32205", d:25, D:52, B:22, type:"tapered"},
  {code:"32206", d:30, D:62, B:25, type:"tapered"},
  {code:"32207", d:35, D:72, B:27, type:"tapered"},
  {code:"32208", d:40, D:80, B:32, type:"tapered"},
  // ---- Angular contact + spherical (common) ----
  {code:"7204", d:20, D:47, B:14, type:"angular"},
  {code:"7205", d:25, D:52, B:15, type:"angular"},
  {code:"22205", d:25, D:52, B:18, type:"spherical"},
  {code:"22206", d:30, D:62, B:20, type:"spherical"},
  {code:"22207", d:35, D:72, B:23, type:"spherical"},
  {code:"UC204", d:20, D:47, B:31, type:"insert"},
  {code:"UC205", d:25, D:52, B:34.1, type:"insert"},
  {code:"UC206", d:30, D:62, B:38.1, type:"insert"}
];

window.TYPE_META = {
  deep:    {en:"Deep Groove Ball Bearing", ar:"رولمان بلي كروي — مجرى عميق"},
  mini:    {en:"Miniature Ball Bearing", ar:"رولمان بلي ميني / صغير"},
  thin:    {en:"Thin-Section Ball Bearing (68/69)", ar:"رولمان بلي رفيع — سلسلة 68/69"},
  thin16000:{en:"Extra-Light Ball Bearing (16000)", ar:"رولمان بلي خفيف — سلسلة 16000"},
  tapered: {en:"Tapered Roller Bearing", ar:"رولمان بلي مخروطي (تايبر)"},
  angular: {en:"Angular Contact Ball Bearing", ar:"رولمان بلي تلامس زاوي"},
  spherical:{en:"Spherical Roller Bearing", ar:"رولمان بلي كروي الأسطوانات"},
  insert:  {en:"Insert Ball Bearing (UC)", ar:"رولمان بلي كراسي (UC)"}
};

/* Suffix guide */
window.SUFFIXES = [
  {s:"2RS / 2RS1 / LLU / DDU / 2NSE", en:"Dual rubber seals — dust & water resistant, greased for life", ar:"كاوتش مزدوج — ضد التراب والمياه، مشحّم مدى الحياة"},
  {s:"ZZ / 2Z", en:"Dual metal shields — high speed, light dust protection", ar:"غطاء معدني مزدوج — سرعات عالية وحماية خفيفة"},
  {s:"RS / RSR / LU", en:"Single rubber seal, one side open", ar:"كاوتش ناحية واحدة"},
  {s:"Z / ZR", en:"Single metal shield", ar:"غطاء معدني ناحية واحدة"},
  {s:"C3", en:"Internal clearance greater than normal — for heat / press fit", ar:"خلوص داخلي أكبر من العادي — للحرارة والشحط"},
  {s:"C4", en:"Even greater clearance — heavy heat / high speed", ar:"خلوص أكبر — حرارة عالية"},
  {s:"K", en:"Tapered bore 1:12 — for adapter sleeve mounting", ar:"ثقب مخروطي — للتركيب بجلبة"},
  {s:"N / NR", en:"Snap-ring groove (+ring) on outer ring", ar:"مجرى تيلة على الحلقة الخارجية"},
  {s:"P5 / P6", en:"Precision tolerance class (tighter than normal)", ar:"درجة دقة عالية"},
  {s:"TN9 / TVP / G15", en:"Polyamide / reinforced cage — quiet, light", ar:"قفص بولي أميد — خفيف وهادئ"},
  {s:"J2 / JR", en:"Pressed steel cage (tapered bearings)", ar:"قفص صاج — للرولمان المخروطي"},
  {s:"E", en:"Reinforced / increased load design", ar:"تصميم مقوّى بحمولة أعلى"}
];

/* Brand cross-reference pattern (base code is universal) */
window.BRANDS = ["SKF","FAG","NSK","NTN","Koyo","Nachi"];
window.brandVariant = function(base, brand){
  const map = {
    "SKF": base + "-2RS1",
    "FAG": base + "-2RSR",
    "NSK": base + "DDU",
    "NTN": base + "LLU",
    "Koyo": base + " 2RS",
    "Nachi": base + "-2NSE"
  };
  return map[brand] || base;
};
