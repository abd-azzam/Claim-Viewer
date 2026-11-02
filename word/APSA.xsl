<?xml version="1.0" encoding="utf-8"?>
<!-- APSA author-date adaptations of the user's installed Chicago renderer.
     Rules: https://connect.apsanet.org/stylemanual/sample-page/paranthetical-citations/
     and https://connect.apsanet.org/stylemanual/sample-page/references/.
     Microsoft's stylesheet is loaded locally and is not redistributed. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
 xmlns:b="http://schemas.openxmlformats.org/officeDocument/2006/bibliography"
 xmlns:msxsl="urn:schemas-microsoft-com:xslt" exclude-result-prefixes="b msxsl">
 <!-- The installer merges these overrides into the locally installed renderer. -->
 <xsl:template match="/">
  <xsl:choose>
   <xsl:when test="b:OfficeStyleKey"><xsl:text>American Political Science Association (APSA)</xsl:text></xsl:when>
   <xsl:when test="b:StyleNameLocalized"><xsl:text>American Political Science Association (APSA)</xsl:text></xsl:when>
   <xsl:when test="b:Version"><xsl:text>2026.11.02</xsl:text></xsl:when>
   <xsl:when test="b:Citation">
    <xsl:variable name="populated"><xsl:call-template name="populateMain"><xsl:with-param name="Type">b:Citation</xsl:with-param></xsl:call-template></xsl:variable>
    <html xmlns="http://www.w3.org/TR/REC-html40"><body><p>
     <xsl:for-each select="msxsl:node-set($populated)/b:Citation">
      <xsl:if test="b:FirstAuthor"><xsl:text>(</xsl:text></xsl:if>
      <xsl:value-of select="b:PagePrefix"/>
      <xsl:if test="not(b:NoAuthor)">
       <xsl:choose>
        <xsl:when test="b:Source/b:Author/b:Main/b:Corporate"><xsl:value-of select="b:Source/b:Author/b:Main/b:Corporate"/></xsl:when>
        <xsl:when test="b:Source/b:Author/b:Main/b:NameList/b:Person">
         <xsl:variable name="people" select="b:Source/b:Author/b:Main/b:NameList/b:Person"/>
         <xsl:variable name="minimum"><xsl:choose><xsl:when test="b:MinAuthors &gt; 1"><xsl:value-of select="b:MinAuthors"/></xsl:when><xsl:otherwise>1</xsl:otherwise></xsl:choose></xsl:variable>
         <xsl:for-each select="$people[count($people) &lt; 4 or position() &lt;= number($minimum)]">
          <xsl:if test="position() &gt; 1"><xsl:choose><xsl:when test="position()=last() and count($people) &lt; 4"><xsl:if test="count($people)=3">,</xsl:if><xsl:text> and </xsl:text></xsl:when><xsl:otherwise>, </xsl:otherwise></xsl:choose></xsl:if>
          <xsl:value-of select="b:Last"/>
         </xsl:for-each>
         <xsl:if test="count($people) &gt; 3"><xsl:text> et al.</xsl:text></xsl:if>
        </xsl:when>
        <xsl:otherwise><xsl:value-of select="b:Source/b:Title"/></xsl:otherwise>
       </xsl:choose>
       <xsl:if test="not(b:NoYear)"><xsl:text> </xsl:text></xsl:if>
      </xsl:if>
      <xsl:if test="not(b:NoYear)"><xsl:choose><xsl:when test="b:Source/b:Year"><xsl:value-of select="b:Source/b:Year"/></xsl:when><xsl:otherwise>n.d.</xsl:otherwise></xsl:choose></xsl:if>
      <xsl:if test="string-length(b:Pages) &gt; 0"><xsl:text>, </xsl:text><xsl:value-of select="b:Pages"/></xsl:if>
      <xsl:value-of select="b:PageSuffix"/>
      <xsl:choose><xsl:when test="b:LastAuthor"><xsl:text>)</xsl:text></xsl:when><xsl:otherwise><xsl:text>; </xsl:text></xsl:otherwise></xsl:choose>
     </xsl:for-each>
    </p></body></html>
   </xsl:when>
   <xsl:otherwise><xsl:call-template name="claimViewerChicago"/></xsl:otherwise>
  </xsl:choose>
 </xsl:template>
 <!-- APSA repeats the names, rather than replacing them with a dash. -->
 <xsl:template name="templ_prop_Chicago_SameAuthor"><xsl:param name="LCID"/><xsl:call-template name="formatMain"/></xsl:template>
 <xsl:template name="formatPersonsAuthor">
  <xsl:choose>
   <xsl:when test="b:Corporate"><xsl:value-of select="b:Corporate"/></xsl:when>
   <xsl:otherwise>
    <xsl:variable name="people" select="b:NameList/b:Person"/>
    <xsl:for-each select="$people[count($people) &lt; 10 or position() &lt;= 7]">
     <xsl:if test="position() &gt; 1"><xsl:choose><xsl:when test="position()=last() and count($people) &lt; 10"><xsl:if test="count($people) &gt; 2">,</xsl:if><xsl:text> and </xsl:text></xsl:when><xsl:otherwise>, </xsl:otherwise></xsl:choose></xsl:if>
     <xsl:choose><xsl:when test="position()=1"><xsl:call-template name="formatMainAuthor"/></xsl:when><xsl:otherwise><xsl:call-template name="formatOtherAuthors"/></xsl:otherwise></xsl:choose>
    </xsl:for-each>
    <xsl:if test="count($people) &gt;= 10"><xsl:text>, et al.</xsl:text></xsl:if>
   </xsl:otherwise>
  </xsl:choose>
 </xsl:template>
</xsl:stylesheet>
