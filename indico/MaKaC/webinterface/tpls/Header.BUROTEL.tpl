<%include file="Announcement.tpl"/>

<div class="page-header clearfix" style="background-color: #36798C;">
        <%include file="SessionBar.tpl" args="dark=False"/>

        <!--
            set fixed height on anchor to assure that the height is
            corrected if the image cannot be retrieved (i.e. https problems) -->
        <a style="min-height: 60px;" href="${ urlHandlers.UHWelcome.getURL() }">
            <img class="header-logo" src="${ systemIcon('burotel.png') }" />
        </a>

    <div class="global-menu toolbar">

        % if roomBooking:
            <a href="${ urlHandlers.UHRoomBookingWelcome.getURL() }">${ _("Room booking") }</a>
        % endif
        
        % if len(adminItemList) == 1:
            <a href="${ adminItemList[0]['url'] }">${ adminItemList[0]['text'] }</a>
        % elif len(adminItemList) > 1:
            <a class="arrow" href="#" data-toggle="dropdown">${ _("Administration") }</a>
            <ul class="dropdown">
            % for item in adminItemList:
                <li><a href="${ item['url'] }">${ item['text'] }</a></li>
            % endfor
            </ul>
        % endif
    </div>
</div>
