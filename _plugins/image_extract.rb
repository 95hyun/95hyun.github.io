module Jekyll
  module ImageExtractFilter
    def extract_first_image(content)
      return nil if content.nil? || content.empty?
      
      # HTML img 태그에서 src 추출
      img_match = content.match(/<img[^>]+src\s*=\s*['"]+([^'"]+)['"]/i)
      return img_match[1] if img_match
      
      # 마크다운 이미지 문법에서 추출
      md_match = content.match(/!\[[^\]]*\]\(([^)]+)\)/)
      return md_match[1] if md_match
      
      nil
    end
    
    def has_images(content)
      return false if content.nil? || content.empty?
      
      # HTML img 태그 또는 마크다운 이미지 문법이 있는지 확인
      content.match?(/<img[^>]+src/i) || content.match?(/!\[[^\]]*\]\([^)]+\)/)
    end
  end
end

Liquid::Template.register_filter(Jekyll::ImageExtractFilter)