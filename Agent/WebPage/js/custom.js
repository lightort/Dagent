// Custom Script
// Developed by: Samson.Onna
// CopyRights : http://webthemez.com

/*
Theme by: WebThemez.com
Note: Please use our back link in your site
*/
$( function() {
        var endDate = "December  27, 2027 15:03:25";

        $('.countdown.simple').countdown({ date: endDate });

        $('.countdown.styled').countdown({
          date: endDate,
          render: function(data) {
            $(this.el).html("<div>" + this.leadingZeros(data.days, 3) + " <span>days</span></div><div>" + this.leadingZeros(data.hours, 2) + " <span>hrs</span></div><div>" + this.leadingZeros(data.min, 2) + " <span>min</span></div><div>" + this.leadingZeros(data.sec, 2) + " <span>sec</span></div>");
          }
        });

        $('.countdown.callback').countdown({
          date: +(new Date) + 10000,
          render: function(data) {
            $(this.el).text(this.leadingZeros(data.sec, 2) + " sec");
          },
          onEnd: function() {
            $(this.el).addClass('ended');
          }
        }).on("click", function() {
          $(this).removeClass('ended').data('countdown').update(+(new Date) + 10000).start();
        });
		
		
		
      });
   
   
var customScripts = {
 
    onePageNav: function () {

        $('#mainNav').onePageNav({
            currentClass: 'active',
            changeHash: false,
            scrollSpeed: 950,
            scrollThreshold: 0.2,
            filter: '',
            easing: 'swing',
            begin: function () {
                //I get fired when the animation is starting
            },
            end: function () {
                   //I get fired when the animation is ending
				if(!$('#main-nav ul li:first-child').hasClass('active')){
					$('.header').addClass('addBg');
				}else{
						$('.header').removeClass('addBg');
				}
				
            },
            scrollChange: function ($currentListItem) {
                //I get fired when you enter a section and I pass the list item of the section
				if(!$('#main-nav ul li:first-child').hasClass('active')){
					$('.header').addClass('addBg');
				}else{
						$('.header').removeClass('addBg');
				}
			}
        });
		
		$("a[href='#top']").click(function () {
                $("html, body").animate({ scrollTop: 0 }, "slow");
                return false;
            });
			$("a[href='#basics']").click(function () {
                $("html, body").animate({ scrollTop: $('#services').offset().top}, "slow"); 
                return false;
            });
    },   
	waySlide: function(){
		  	/* Waypoints Animations
		   ------------------------------------------------------ */		   			  			
			$('#services').waypoint(function() {				
			$('#services .col-md-3').addClass( 'animated fadeInUp show' );   
			}, { offset: 800}); 
			$('#aboutUs').waypoint(function() {				
			$('#aboutUs').addClass( 'animated fadeInUp show' );   
			}, { offset: 800}); 
			$('#contactUs').waypoint(function() {				
			$('#contactUs .parlex-back').addClass( 'animated fadeInUp show' );   
			}, { offset: 800}); 
			 						 
		}, 
    init: function () {
        customScripts.onePageNav();  
		customScripts.waySlide(); 
    }
}
$('document').ready(function () {
	 $.backstretch([
      "images/img1.jpg"
    , "images/img2.jpg"
    , "images/img3.jpg"
  ], {duration: 3000, fade: 1250});
  
    customScripts.init();
$("#firstLink a").on("click", function () {
    $("#mainNav").css("border-color", "#ffffff");
});
	$('#services .col-md-3, #features, #aboutUs, #clients, #portfolio, #plans, #contactUs .parlex-back').css('opacity','0');
	$( "#menuToggle" ).toggle(function() {
	$(this).find('i').removeClass('fa-bars').addClass('fa-remove');
	 $('#mainNav').animate({"right":"0px"}, "slow");
	}, function() {
	  $('#mainNav').animate({"right":"-200px"}, "slow");
	  $(this).find('i').removeClass('fa-remove').addClass('fa-bars');
	});	
});
(function () {
  const TOKEN_VERSION = "WTZ1";
  const CLIENT_SECRET = "alive-template::contact-form::v1";
  const TOKEN_TTL_MS = 5 * 60 * 1000;

  function normalizeText(value) {
    return String(value || "")
      .trim()
      .replace(/\r\n/g, "\n")
      .replace(/\s+/g, " ");
  }

  function normalizeEmail(value) {
    return normalizeText(value).toLowerCase();
  }

  function reverseString(str) {
    return str.split("").reverse().join("");
  }

  function rotateString(str, step) {
    if (!str || !str.length) return str;
    var n = step % str.length;
    return str.slice(n) + str.slice(0, n);
  }

  function xorFold(str) {
    var out = [];
    for (var i = 0; i < str.length; i++) {
      var code = str.charCodeAt(i);
      var mixed = (code ^ ((i * 31 + 17) & 0xff)).toString(16);
      out.push(("00" + mixed).slice(-2));
    }
    return out.join("");
  }

  function checksum32(str) {
    var hash = 0x811c9dc5;
    for (var i = 0; i < str.length; i++) {
      hash ^= str.charCodeAt(i);
      hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
      hash >>>= 0;
    }
    return ("00000000" + hash.toString(16)).slice(-8);
  }

  function safeEqual(a, b) {
    if (typeof a !== "string" || typeof b !== "string") return false;
    if (a.length !== b.length) return false;
    var diff = 0;
    for (var i = 0; i < a.length; i++) {
      diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }
    return diff === 0;
  }

  async function sha256Hex(text) {
    var data = new TextEncoder().encode(text);
    var digest = await crypto.subtle.digest("SHA-256", data);
    var bytes = Array.from(new Uint8Array(digest));
    return bytes.map(function (b) {
      return b.toString(16).padStart(2, "0");
    }).join("");
  }

  function buildCanonicalPayload(name, email, comment, ts) {
    var n = normalizeText(name);
    var e = normalizeEmail(email);
    var c = normalizeText(comment);
    var tsStr = String(ts);

    var layer1 = [
      "v=" + TOKEN_VERSION,
      "ts=" + tsStr,
      "nl=" + n.length,
      "el=" + e.length,
      "cl=" + c.length,
      "n=" + n,
      "e=" + e,
      "c=" + c
    ].join("|");

    var layer2 = [
      reverseString(n),
      rotateString(e, 3),
      reverseString(c),
      tsStr.split("").reverse().join("")
    ].join("::");

    var layer3 = xorFold(layer1 + "##" + layer2);

    return {
      canonical: layer1,
      mixed: layer2,
      folded: layer3
    };
  }

  async function generateToken(name, email, comment, ts) {
    var payload = buildCanonicalPayload(name, email, comment, ts);
    var stageA = checksum32(payload.canonical);
    var stageB = checksum32(payload.mixed);

    var material = [
      TOKEN_VERSION,
      payload.canonical,
      payload.mixed,
      payload.folded,
      stageA,
      stageB,
      CLIENT_SECRET
    ].join("||");

    var digest = await sha256Hex(material);
    var ts36 = Number(ts).toString(36);
    var shortCheck = checksum32(digest + "::" + ts36).slice(0, 10);
    var body = (
      digest.slice(0, 12) +
      payload.folded.slice(0, 16) +
      digest.slice(12, 28) +
      stageA +
      stageB +
      digest.slice(-12)
    ).toLowerCase();

    return [TOKEN_VERSION, ts36, shortCheck, body].join(".");
  }

  async function validateToken(name, email, comment, ts, token) {
    if (!token || !ts) {
      return { valid: false, reason: "missing_token_or_timestamp" };
    }

    var now = Date.now();
    var age = now - Number(ts);

    if (!Number(ts) || age < 0 || age > TOKEN_TTL_MS) {
      return { valid: false, reason: "expired_or_invalid_timestamp" };
    }

    var expected = await generateToken(name, email, comment, ts);
    var ok = safeEqual(expected, token);

    return {
      valid: ok,
      reason: ok ? "ok" : "token_mismatch"
    };
  }

  function showResult(html, success) {
    $(".result").html(html).css({
      marginTop: "15px",
      padding: "12px",
      borderRadius: "4px",
      wordBreak: "break-all",
      background: success ? "#28a745" : "#d9534f",
      color: "#fff"
    });
  }

  $("#contactfrm").on("submit", async function (e) {
    e.preventDefault();

    var name = $("#name").val();
    var email = $("#email").val();
    var comment = $("#comments").val();

    if (!normalizeText(name) || !normalizeEmail(email) || !normalizeText(comment)) {
      showResult("Please fill in name, email and comments.", false);
      return;
    }

    try {
      var ts = Date.now();
      var token = await generateToken(name, email, comment, ts);
      var verify = await validateToken(name, email, comment, ts, token);

      if (!verify.valid) {
        showResult("Token validation failed: " + verify.reason, false);
        return;
      }

      showResult(
        "<strong>Submit success</strong><br><br>" +
        "<strong>Name:</strong> " + $("<div>").text(name).html() + "<br>" +
        "<strong>Email:</strong> " + $("<div>").text(email).html() + "<br>" +
        "<strong>Comments:</strong> " + $("<div>").text(comment).html() + "<br>" +
        "<strong>Timestamp:</strong> " + ts + "<br>" +
        "<strong>Token:</strong> " + $("<div>").text(token).html(),
        true
      );
    } catch (err) {
      showResult("Error: " + err.message, false);
    }
  });
})();
