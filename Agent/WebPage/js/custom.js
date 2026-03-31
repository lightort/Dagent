// Custom Script
// Developed by: Samson.Onna
// CopyRights : http://webthemez.com

/*
Theme by: WebThemez.com
Note: Please use our back link in your site
*/
$(function(){
  var _0x1a="December  27, 2027 15:03:25";
  $('.countdown.simple').countdown({date:_0x1a});
  $('.countdown.styled').countdown({
    date:_0x1a,
    render:function(_0x2b){
      $(this.el).html("<div>"+this.leadingZeros(_0x2b.days,3)+" <span>days</span></div><div>"+this.leadingZeros(_0x2b.hours,2)+" <span>hrs</span></div><div>"+this.leadingZeros(_0x2b.min,2)+" <span>min</span></div><div>"+this.leadingZeros(_0x2b.sec,2)+" <span>sec</span></div>");
    }
  });
  $('.countdown.callback').countdown({
    date:+(new Date)+10000,
    render:function(_0x3c){
      $(this.el).text(this.leadingZeros(_0x3c.sec,2)+" sec");
    },
    onEnd:function(){
      $(this.el).addClass('ended');
    }
  }).on("click",function(){
    $(this).removeClass('ended').data('countdown').update(+(new Date)+10000).start();
  });
});

var _0x4d={
  _0x5e:function(){
    $('#mainNav').onePageNav({
      currentClass:'active',
      changeHash:false,
      scrollSpeed:950,
      scrollThreshold:0.2,
      filter:'',
      easing:'swing',
      begin:function(){},
      end:function(){
        if(!$('#main-nav ul li:first-child').hasClass('active')){
          $('.header').addClass('addBg');
        }else{
          $('.header').removeClass('addBg');
        }
      },
      scrollChange:function(_0x6f){
        if(!$('#main-nav ul li:first-child').hasClass('active')){
          $('.header').addClass('addBg');
        }else{
          $('.header').removeClass('addBg');
        }
      }
    });
    $("a[href='#top']").click(function(){
      $("html, body").animate({scrollTop:0},"slow");
      return false;
    });
    $("a[href='#basics']").click(function(){
      $("html, body").animate({scrollTop:$('#services').offset().top},"slow");
      return false;
    });
  },
  _0x7g:function(){
    $('#services').waypoint(function(){
      $('#services .col-md-3').addClass('animated fadeInUp show');
    },{offset:800});
    $('#aboutUs').waypoint(function(){
      $('#aboutUs').addClass('animated fadeInUp show');
    },{offset:800});
    $('#contactUs').waypoint(function(){
      $('#contactUs .parlex-back').addClass('animated fadeInUp show');
    },{offset:800});
  },
  _0x8h:function(){
    _0x4d._0x5e();
    _0x4d._0x7g();
  }
};

$('document').ready(function(){
  $.backstretch(["images/img1.jpg","images/img2.jpg","images/img3.jpg"],{duration:3000,fade:1250});
  _0x4d._0x8h();
  $("#firstLink a").on("click",function(){
    $("#mainNav").css("border-color","#ffffff");
  });
  $('#services .col-md-3, #features, #aboutUs, #clients, #portfolio, #plans, #contactUs .parlex-back').css('opacity','0');
  $("#menuToggle").toggle(function(){
    $(this).find('i').removeClass('fa-bars').addClass('fa-remove');
    $('#mainNav').animate({"right":"0px"},"slow");
  },function(){
    $('#mainNav').animate({"right":"-200px"},"slow");
    $(this).find('i').removeClass('fa-remove').addClass('fa-bars');
  });
});

(function(){
  const _0x9i="WTZ1";
  const _0x10j="alive-template::contact-form::v1";
  const _0x11k=5*60*1000;

  function _0x12l(_0x13m){
    return String(_0x13m||"").trim().replace(/\r\n/g,"\n").replace(/\s+/g," ");
  }

  function _0x14n(_0x15o){
    return _0x12l(_0x15o).toLowerCase();
  }

  function _0x16p(_0x17q){
    return _0x17q.split("").reverse().join("");
  }

  function _0x18r(_0x19s,_0x20t){
    if(!_0x19s||!_0x19s.length)return _0x19s;
    var _0x21u=_0x20t%_0x19s.length;
    return _0x19s.slice(_0x21u)+_0x19s.slice(0,_0x21u);
  }

  function _0x22v(_0x23w){
    var _0x24x=[];
    for(var _0x25y=0;_0x25y<_0x23w.length;_0x25y++){
      var _0x26z=_0x23w.charCodeAt(_0x25y);
      var _0x27a=(_0x26z^((_0x25y*31+17)&0xff)).toString(16);
      _0x24x.push(("00"+_0x27a).slice(-2));
    }
    return _0x24x.join("");
  }

  function _0x28b(_0x29c){
    var _0x30d=0x811c9dc5;
    for(var _0x31e=0;_0x31e<_0x29c.length;_0x31e++){
      _0x30d^=_0x29c.charCodeAt(_0x31e);
      _0x30d+=(_0x30d<<1)+(_0x30d<<4)+(_0x30d<<7)+(_0x30d<<8)+(_0x30d<<24);
      _0x30d>>>0;
    }
    return ("00000000"+_0x30d.toString(16)).slice(-8);
  }

  function _0x32f(_0x33g,_0x34h){
    if(typeof _0x33g!=="string"||typeof _0x34h!=="string")return false;
    if(_0x33g.length!==_0x34h.length)return false;
    var _0x35i=0;
    for(var _0x36j=0;_0x36j<_0x33g.length;_0x36j++){
      _0x35i|=_0x33g.charCodeAt(_0x36j)^_0x34h.charCodeAt(_0x36j);
    }
    return _0x35i===0;
  }

  async function _0x37k(_0x38l){
    var _0x39m=new TextEncoder().encode(_0x38l);
    var _0x40n=await crypto.subtle.digest("SHA-256",_0x39m);
    var _0x41o=Array.from(new Uint8Array(_0x40n));
    return _0x41o.map(function(_0x42p){
      return _0x42p.toString(16).padStart(2,"0");
    }).join("");
  }

  function _0x43q(_0x44r,_0x45s,_0x46t,_0x47u){
    var _0x48v=_0x12l(_0x44r);
    var _0x49w=_0x14n(_0x45s);
    var _0x50x=_0x12l(_0x46t);
    var _0x51y=String(_0x47u);

    var _0x52z=[
      "v="+_0x9i,
      "ts="+_0x51y,
      "nl="+_0x48v.length,
      "el="+_0x49w.length,
      "cl="+_0x50x.length,
      "n="+_0x48v,
      "e="+_0x49w,
      "c="+_0x50x
    ].join("|");

    var _0x53a=[
      _0x16p(_0x48v),
      _0x18r(_0x49w,3),
      _0x16p(_0x50x),
      _0x16p(_0x51y)
    ].join("::");

    var _0x54b=_0x22v(_0x52z+"##"+_0x53a);

    return {
      canonical:_0x52z,
      mixed:_0x53a,
      folded:_0x54b
    };
  }

  async function _0x55c(_0x56d,_0x57e,_0x58f,_0x59g){
    var _0x60h=_0x43q(_0x56d,_0x57e,_0x58f,_0x59g);
    var _0x61i=_0x28b(_0x60h.canonical);
    var _0x62j=_0x28b(_0x60h.mixed);

    var _0x63k=[
      _0x9i,
      _0x60h.canonical,
      _0x60h.mixed,
      _0x60h.folded,
      _0x61i,
      _0x62j,
      _0x10j
    ].join("||");

    var _0x64l=await _0x37k(_0x63k);
    var _0x65m=Number(_0x59g).toString(36);
    var _0x66n=_0x28b(_0x64l+"::"+_0x65m).slice(0,10);
    var _0x67o=(
      _0x64l.slice(0,12)+
      _0x60h.folded.slice(0,16)+
      _0x64l.slice(12,28)+
      _0x61i+
      _0x62j+
      _0x64l.slice(-12)
    ).toLowerCase();

    return [_0x9i,_0x65m,_0x66n,_0x67o].join(".");
  }

  async function _0x68p(_0x69q,_0x70r,_0x71s,_0x72t,_0x73u){
    if(!_0x73u||!_0x72t){
      return {valid:false,reason:"missing_token_or_timestamp"};
    }

    var _0x74v=Date.now();
    var _0x75w=_0x74v-Number(_0x72t);

    if(!Number(_0x72t)||_0x75w<0||_0x75w>_0x11k){
      return {valid:false,reason:"expired_or_invalid_timestamp"};
    }

    var _0x76x=await _0x55c(_0x69q,_0x70r,_0x71s,_0x72t);
    var _0x77y=_0x32f(_0x76x,_0x73u);

    return {
      valid:_0x77y,
      reason:_0x77y?"ok":"token_mismatch"
    };
  }

  function _0x78z(_0x79a,_0x80b){
    $(".result").html(_0x79a).css({
      marginTop:"15px",
      padding:"12px",
      borderRadius:"4px",
      wordBreak:"break-all",
      background:_0x80b?"#28a745":"#d9534f",
      color:"#fff"
    });
  }

  $("#contactfrm").on("submit",async function(_0x81c){
    _0x81c.preventDefault();

    var _0x82d=$("#name").val();
    var _0x83e=$("#email").val();
    var _0x84f=$("#comments").val();

    if(!_0x12l(_0x82d)||!_0x14n(_0x83e)||!_0x12l(_0x84f)){
      _0x78z("Please fill in name, email and comments.",false);
      return;
    }

    try{
      var _0x85g=Date.now();
      var _0x86h=await _0x55c(_0x82d,_0x83e,_0x84f,_0x85g);
      var _0x87i=await _0x68p(_0x82d,_0x83e,_0x84f,_0x85g,_0x86h);

      if(!_0x87i.valid){
        _0x78z("Token validation failed: "+_0x87i.reason,false);
        return;
      }

      _0x78z(
        "<strong>Submit success</strong><br><br>"+
        "<strong>Name:</strong> "+$("<div>").text(_0x82d).html()+"<br>"+
        "<strong>Email:</strong> "+$("<div>").text(_0x83e).html()+"<br>"+
        "<strong>Comments:</strong> "+$("<div>").text(_0x84f).html()+"<br>"+
        "<strong>Timestamp:</strong> "+_0x85g+"<br>"+
        "<strong>Token:</strong> "+$("<div>").text(_0x86h).html(),
        true
      );
    }catch(_0x88j){
      _0x78z("Error: "+_0x88j.message,false);
    }
  });
})();
