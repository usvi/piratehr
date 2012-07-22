jQuery.webshims.register("form-native-fix",function(b,c,g,q,e){if(Modernizr.formvalidation&&!Modernizr.bugfreeformvalidation&&!c.bugs.bustedValidity){var p=b.browser.webkit,l=[],h,m,f;if(g.addEventListener){var n=e,o=!1;g.addEventListener("submit",function(a){if(!o&&a.target.checkValidity&&null==b.attr(a.target,"novalidate")&&(f=!0,b("input:invalid, select:invalid, textarea:invalid",a.target).length&&(b(a.target).unbind("submit.preventInvalidSubmit").bind("submit.preventInvalidSubmit",function(j){null==
b.attr(a.target,"novalidate")&&(j.stopImmediatePropagation(),p&&j.preventDefault());a.target&&b(a.target).unbind("submit.preventInvalidSubmit")}),c.moveToFirstEvent(a.target,"submit")),f=!1,!g.opera))c.fromSubmit=!0,b(a.target).checkValidity(),c.fromSubmit=!1},!0);e=function(a){null!=b.attr(a.target,"formnovalidate")&&(n&&clearTimeout(n),o=!0,n=setTimeout(function(){o=!1},20))};g.addEventListener("click",e,!0);g.addEventListener("touchstart",e,!0);g.addEventListener("touchend",e,!0)}b(document).bind("firstinvalidsystem",
function(a,b){if(m=b.form)h=!1,l=[],c.fromSubmit&&(h=b)}).bind("invalid",function(a){-1==l.indexOf(a.target)?l.push(a.target):a.stopImmediatePropagation()}).bind("lastinvalid",function(a,j){var i=j.invalidlist[0];i&&(p||b.nodeName(i,"select"))&&b(i).not(":focus")&&h&&!h.isInvalidUIPrevented()&&c.validityAlert.showFor(i);h=!1;l=[];m&&b(m).unbind("submit.preventInvalidSubmit")});b.browser.webkit&&Modernizr.inputtypes.date&&(function(){var a={updateInput:1,input:1},c={date:1,time:1,"datetime-local":1},
i={focusout:1,blur:1},g={updateInput:1,change:1},e=function(b){var c,e=!0,d=b.prop("value"),j=d,k=function(c){if(b){var f=b.prop("value");f!==d&&(d=f,(!c||!a[c.type])&&b.trigger("input"));c&&g[c.type]&&(j=f);!e&&f!==j&&b.trigger("change")}},h,f=function(a){clearInterval(c);setTimeout(function(){a&&i[a.type]&&(e=!1);b&&(b.unbind("focusout blur",f).unbind("input change updateInput",k),k());b=null},1)};clearInterval(c);c=setInterval(k,160);clearTimeout(h);h=setTimeout(k,9);b.unbind("focusout blur",f).unbind("input change updateInput",
k);b.bind("focusout blur",f).bind("input updateInput change",k)};if(b.event.customEvent)b.event.customEvent.updateInput=!0;b(q).bind("focusin",function(a){a.target&&c[a.target.type]&&!a.target.readOnly&&!a.target.disabled&&e(b(a.target))})}(),function(){var a=function(a){var c=1,e,d;if("date"==a.type&&(f||!b(a).is(":focus")))if((d=a.value)&&10>d.length&&(d=d.split("-"))&&3==d.length){for(;3>c;c++)if(1==d[c].length)d[c]="0"+d[c];else if(2!=d[c].length){e=!0;break}if(!e)return d=d.join("-"),b.prop(a,
"value",d),d}},e,i,g,h;e=c.defineNodeNameProperty("input","checkValidity",{prop:{value:function(){a(this);return e.prop._supvalue.apply(this,arguments)}}});i=c.defineNodeNameProperty("form","checkValidity",{prop:{value:function(){b("input",this).each(function(){a(this)});return i.prop._supvalue.apply(this,arguments)}}});g=c.defineNodeNameProperty("input","value",{prop:{set:function(){return g.prop._supset.apply(this,arguments)},get:function(){return a(this)||g.prop._supget.apply(this,arguments)}}});
h=c.defineNodeNameProperty("input","validity",{prop:{writeable:!1,get:function(){a(this);return h.prop._supget.apply(this,arguments)}}});b(document).bind("change",function(b){f=!0;a(b.target);f=!1})}())}});
