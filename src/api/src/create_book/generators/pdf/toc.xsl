<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:outline="http://wkhtmltopdf.org/outline"
                xmlns="http://www.w3.org/1999/xhtml">
  <xsl:output doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN"
              doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
              indent="yes" />
  <xsl:template match="outline:outline">
    <html>
      <head>
<style>
@font-face {
  font-family: 'PT Serif';
  src: url('./fonts/PTSerif-Regular.ttf') format('truetype');
  font-weight: 400;
  font-style: normal;
}

@font-face {
  font-family: 'PT Serif';
  src: url('./fonts/PTSerif-Bold.ttf') format('truetype');
  font-weight: 700;
  font-style: normal;
}

@font-face {
  font-family: 'PT Serif';
  src: url('./fonts/PTSerif-Italic.ttf') format('truetype');
  font-weight: 400;
  font-style: italic;
}

@font-face {
  font-family: 'PT Serif';
  src: url('./fonts/PTSerif-BoldItalic.ttf') format('truetype');
  font-weight: 700;
  font-style: italic;
}

.pt-serif-regular {
  font-family: "PT Serif", serif;
  font-weight: 400;
  font-style: normal;
}

.pt-serif-bold {
  font-family: "PT Serif", serif;
  font-weight: 700;
  font-style: normal;
}

.pt-serif-regular-italic {
  font-family: "PT Serif", serif;
  font-weight: 400;
  font-style: italic;
}

.pt-serif-bold-italic {
  font-family: "PT Serif", serif;
  font-weight: 700;
  font-style: italic;
}


h1 {
  text-align: center;
  font-family: "PT Serif", serif !important;
  font-weight: 700 !important;
  font-style: normal !important;
  font-size: 36px !important; /* Uniform size */
  margin-bottom: 20px; /* Space below the heading */
  border-bottom: 4px solid black; /* Black line */
  padding-bottom: 10px; /* Space between text and line */
}


          div {border-bottom: 1px dashed rgb(100,000,100);
          padding-top: 5px;}
          span {float: right;}
          li {list-style: none;}
          ul {
            font-size: 22px;
            font-family: arial;
          }
          ul ul {font-size: 80%; }
          ul {padding-left: 0em;}
          ul ul {padding-left: 1em;}
          a {text-decoration:none; color: black;}
        </style>
      </head>
      <body>
        <h1>Table of Contents</h1>
        <ul><xsl:apply-templates select="outline:item/outline:item"/></ul>
      </body>
    </html>
  </xsl:template>
  <xsl:template match="outline:item">
    <li>
      <xsl:if test="@title!=''">
        <div>
          <a class="pt-serif-regular">
            <xsl:if test="@link">
              <xsl:attribute name="href"><xsl:value-of select="@link"/></xsl:attribute>
            </xsl:if>
            <xsl:if test="@backLink">
              <xsl:attribute name="name"><xsl:value-of select="@backLink"/></xsl:attribute>
            </xsl:if>
            <xsl:value-of select="@title" /> 
          </a>
          <span> <xsl:value-of select="@page" /> </span>
        </div>
      </xsl:if>
      <ul>
        <xsl:comment>added to prevent self-closing tags in QtXmlPatterns</xsl:comment>
        <xsl:apply-templates select="outline:item"/>
      </ul>
    </li>
  </xsl:template>
</xsl:stylesheet>
